"""Standalone KSP manual flight demo. Run: python demo.py"""
import argparse
import json
import math
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pybullet as p

from controls import SASController, attitude_rcs_indices, windows_caps_trigger
from effects import EngineFlameVisualizer, GuiCameraController

ASSETS=Path(__file__).resolve().parent/'assets'
DT=1/240
SPAWN=(29.,-46.)


def build_ksp():
    recipe=json.loads((ASSETS/'ksp_scene.json').read_text(encoding='utf-8'))
    if recipe['format']!='ksp-manual-scene-v1':
        raise ValueError('Unsupported scene resource')
    maps={'collision':{-1:-1},'visual':{-1:-1},'body':{}}
    body=None
    for call in recipe['calls']:
        op=call['operation']; args=list(call['args']); kw=dict(call['kwargs'])
        if op in ('createCollisionShape','createVisualShape'):
            kind='collision' if op=='createCollisionShape' else 'visual'
            maps[kind][call['result']]=getattr(p,op)(*args,**kw)
        elif op=='createMultiBody':
            for key,kind in [('baseCollisionShapeIndex','collision'),('baseVisualShapeIndex','visual')]:
                kw[key]=maps[kind][kw[key]]
            for key,kind in [('linkCollisionShapeIndices','collision'),('linkVisualShapeIndices','visual')]:
                kw[key]=[maps[kind][v] for v in kw[key]]
            body=p.createMultiBody(**kw)
            maps['body'][call['result']]=body
        elif op in ('changeDynamics','changeVisualShape'):
            args[0]=maps['body'][args[0]]
            getattr(p,op)(*args,**kw)
        else:
            raise ValueError('Unsupported scene operation: '+op)
    return SimpleNamespace(body_id=body,
        engines=[SimpleNamespace(**e) for e in recipe['engines']],
        component_root_transforms=recipe['component_root_transforms'])


def create_scene(gui):
    if p.connect(p.GUI if gui else p.DIRECT)<0:
        raise RuntimeError('Could not open PyBullet')
    p.setRealTimeSimulation(0)
    p.setGravity(0,0,-1.628)
    p.setTimeStep(DT)
    p.setPhysicsEngineParameter(numSolverIterations=100,contactBreakingThreshold=.001,
                                deterministicOverlappingPairs=1)
    if gui:
        p.configureDebugVisualizer(p.COV_ENABLE_GUI,0)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS,1)
        p.configureDebugVisualizer(p.COV_ENABLE_RGB_BUFFER_PREVIEW,0)
        p.configureDebugVisualizer(p.COV_ENABLE_DEPTH_BUFFER_PREVIEW,0)
        p.configureDebugVisualizer(p.COV_ENABLE_SEGMENTATION_MARK_PREVIEW,0)
    heights=np.load(ASSETS/'crater_terrain.npy',allow_pickle=False).astype(np.float32)
    n=heights.shape[0]
    shape=p.createCollisionShape(p.GEOM_HEIGHTFIELD,meshScale=[512/(n-1)]*2+[1],
        heightfieldData=heights.ravel().tolist(),numHeightfieldRows=n,numHeightfieldColumns=n)
    terrain=p.createMultiBody(0,shape,basePosition=[0,0,float((heights.min()+heights.max())/2)])
    p.changeDynamics(terrain,-1,lateralFriction=1.)
    p.changeVisualShape(terrain,-1,rgbaColor=[.72,.72,.70,1],specularColor=[.01]*3)
    ground=p.rayTest([*SPAWN,100],[*SPAWN,-200])[0][3][2]
    for radius,color,dz in [(2.5,[.72,.13,.1,1],.012),(2,[.85,.85,.82,1],.025),(1.3,[.72,.13,.1,1],.038)]:
        marker=p.createVisualShape(p.GEOM_CYLINDER,radius=radius,length=.018,rgbaColor=color)
        p.createMultiBody(0,-1,marker,basePosition=[*SPAWN,ground+dz])
    lander=build_ksp()
    floor=min(p.getAABB(lander.body_id,j)[0][2] for j in range(-1,p.getNumJoints(lander.body_id)))
    pose=([*SPAWN,ground-floor+.025],p.getQuaternionFromEuler([0,0,math.pi]))
    reset(lander,pose)
    return lander,pose


def reset(lander,pose):
    p.resetBasePositionAndOrientation(lander.body_id,*pose)
    p.resetBaseVelocity(lander.body_id,[0,0,0],[0,0,0])


def throttles(lander,keys,throttle,sas):
    if keys.get(p.B3G_SHIFT,0)&p.KEY_IS_DOWN:
        throttle=min(1.,throttle+.5*DT)
    if keys.get(p.B3G_CONTROL,0)&p.KEY_IS_DOWN:
        throttle=max(0.,throttle-.5*DT)
    values=[0.]*len(lander.engines)
    values[0]=1. if keys.get(32,0)&p.KEY_IS_DOWN else throttle
    for i in attitude_rcs_indices(lander,keys):
        values[i]=1.
    return throttle,sas.assist(lander,keys,values)


def advance(lander,values):
    for engine,value in zip(lander.engines,values):
        if value:
            force=(np.array(engine.thrust_direction)*engine.max_thrust*value).tolist()
            p.applyExternalForce(lander.body_id,engine.link_index,force,engine.nozzle_position,p.LINK_FRAME)
    p.stepSimulation()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--speed',type=float,default=.5,help='Playback speed; physics remains 240 Hz (default 0.5)')
    parser.add_argument('--self-test',action='store_true',help='Run a headless smoke test without opening a window')
    args=parser.parse_args()
    if not math.isfinite(args.speed) or args.speed<=0:
        parser.error('--speed must be positive and finite')
    lander,pose=create_scene(not args.self_test)
    try:
        assert len(lander.engines)==17 and lander.engines[0].component_id=='main_engine'
        flames=EngineFlameVisualizer(lander,main_max_length=2.5)
        sas=SASController(); throttle=0.; caps=False; step=0
        camera=GuiCameraController(distance=10,yaw=270,pitch=-16,max_distance=650)
        if args.self_test:
            for step in range(720):
                keys={32:p.KEY_IS_DOWN} if step>240 else {}
                throttle,values=throttles(lander,keys,throttle,sas)
                if keys:
                    assert values[0]==1 and not any(values[1:]), 'Space must not activate RCS'
                if step%4==0:
                    flames.update(values)
                advance(lander,values)
            assert np.isfinite(p.getBasePositionAndOrientation(lander.body_id)[0]).all()
            reset(lander,pose)
            print('PASS: KSP, 17 engines, 512 m terrain, 720 physics steps, Space main-only, reset')
            return
        print('KSP manual demo | fixed mass | lunar gravity | no trained controller')
        print('Shift/Ctrl: throttle | hold Space: main engine only | arrows: tilt | PgUp/PgDn: axial roll')
        print('CapsLock: SAS damping | 1: retrograde | WASD: camera | Q/E: zoom | R: reset | Esc: quit')
        camera.reset(pose[0]); deadline=time.perf_counter(); hud=-1
        while p.isConnected():
            keys=p.getKeyboardEvents()
            if keys.get(27,0)&(p.KEY_IS_DOWN|p.KEY_WAS_TRIGGERED):
                break
            pressed,caps=windows_caps_trigger(caps)
            if pressed and not any(keys.get(k,0)&p.KEY_WAS_TRIGGERED for k in (20,280,65509,1073741881)):
                keys[20]=p.KEY_WAS_TRIGGERED
            if keys.get(ord('r'),0)&p.KEY_WAS_TRIGGERED:
                reset(lander,pose); flames.clear(); sas=SASController(); throttle=0.
            sas.update(keys)
            throttle,values=throttles(lander,keys,throttle,sas)
            if step%4==0:
                flames.update(values)
                pos=p.getBasePositionAndOrientation(lander.body_id)[0]
                camera.update(pos,keys)
            if step%24==0:
                hud=p.addUserDebugText(f'Main {values[0]:.0%} | SAS {sas.mode if sas.enabled else "OFF"}',
                    [0,0,2.4],textColorRGB=[.15,.15,.15],textSize=1.2,
                    parentObjectUniqueId=lander.body_id,replaceItemUniqueId=hud)
            advance(lander,values); step+=1
            deadline+=DT/args.speed
            time.sleep(max(0,deadline-time.perf_counter()))
            if time.perf_counter()-deadline>.2:
                deadline=time.perf_counter()
    finally:
        if p.isConnected():
            p.disconnect()


if __name__=='__main__':
    main()
