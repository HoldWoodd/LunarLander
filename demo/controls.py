"""Manual RCS selection and optional SAS; no learned policy."""
import sys
import numpy as np
import pybullet as p

CAPS_KEYS=(20,280,65509,1073741881)
ATTITUDE_KEYS=(p.B3G_UP_ARROW,p.B3G_DOWN_ARROW,p.B3G_LEFT_ARROW,p.B3G_RIGHT_ARROW,p.B3G_PAGE_UP,p.B3G_PAGE_DOWN)

def attitude_rcs_indices(lander,keys):
    """Body +X is forward, +Y is left, +Z is the rocket longitudinal axis.

    Vertical opposed pairs pitch/tilt the rocket; tangential horizontal pairs
    roll about +Z. Names such as rcs_down describe thrust, not nozzle location.
    """
    requests=[]
    for key,axis,sign in [(p.B3G_UP_ARROW,1,1),(p.B3G_DOWN_ARROW,1,-1),
                          (p.B3G_LEFT_ARROW,0,-1),(p.B3G_RIGHT_ARROW,0,1),
                          (p.B3G_PAGE_UP,2,1),(p.B3G_PAGE_DOWN,2,-1)]:
        if keys.get(key,0)&p.KEY_IS_DOWN:
            requests.append((axis,sign))
    selected=set()
    for i,e in enumerate(lander.engines):
        if e.component_id=='main_engine' or e.component_id.endswith('_main_engine'):
            continue
        position,q=lander.component_root_transforms[e.component_id]
        R=np.array(p.getMatrixFromQuaternion(q)).reshape(3,3)
        direction=R@np.array(e.thrust_direction)
        point=np.array(position)+R@np.array(e.nozzle_position)
        torque=np.cross(point,direction)
        for axis,sign in requests:
            # Only use vertical nozzles for tilt, tangential horizontal nozzles
            # for roll. Opposed arrow keys cancel rather than firing both pairs.
            if (axis,-sign) in requests:
                continue
            correct_plane=abs(direction[2])>.9 if axis!=2 else abs(direction[2])<.1
            if correct_plane and torque[axis]*sign>1e-5:
                selected.add(i)
    return selected

class SASController:
    """RCS-only angular damping or world-velocity retrograde nose pointing."""
    def __init__(self):
        self.enabled=False
        self.mode='damping'
        self.caps_cooldown=0
        self.last_retrograde_target=None

    def update(self,keys):
        self.caps_cooldown=max(0,self.caps_cooldown-1)
        if not self.caps_cooldown and any(keys.get(k,0)&p.KEY_WAS_TRIGGERED for k in CAPS_KEYS):
            self.enabled=not self.enabled
            self.mode='damping'
            self.caps_cooldown=60  # Merge delayed native/Bullet reports of one press.
        if keys.get(ord('1'),0)&p.KEY_WAS_TRIGGERED:
            self.enabled=True
            self.mode='retrograde'
            self.last_retrograde_target=None

    def assist(self,lander,keys,values):
        result=list(values)
        if not self.enabled:
            return result
        # Manual attitude commands always have priority; resume assistance on release.
        if any(keys.get(k,0)&p.KEY_IS_DOWN for k in ATTITUDE_KEYS):
            return result
        _,q=p.getBasePositionAndOrientation(lander.body_id)
        R=np.array(p.getMatrixFromQuaternion(q)).reshape(3,3)
        velocity,omega=p.getBaseVelocity(lander.body_id)
        wb=R.T@np.array(omega)
        desired=np.zeros(3)
        if self.mode=='retrograde':
            nose=R[:,2]
            speed=float(np.linalg.norm(velocity))
            if speed>=.1:
                self.last_retrograde_target=-np.array(velocity)/speed
            elif self.last_retrograde_target is None:
                # At rest there is no retrograde direction: hold the current nose.
                self.last_retrograde_target=nose.copy()
            target=self.last_retrograde_target
            dot=float(np.clip(np.dot(nose,target),-1,1))
            angle=float(np.arccos(dot))
            axis=np.cross(nose,target)
            if np.linalg.norm(axis)>1e-7:
                axis=R.T@(axis/np.linalg.norm(axis))
            elif dot<0:
                # Upright is exactly 180 degrees away: choose a repeatable pitch
                # axis instead of the zero cross-product equilibrium.
                axis=np.array([0.,1.,0.])
            else:
                axis=np.zeros(3)
            desired=axis*min(.30,.45*angle)
        effort=np.clip((desired-wb)/.25,-1,1)
        for axis,(negative,positive) in enumerate(((p.B3G_LEFT_ARROW,p.B3G_RIGHT_ARROW),
                                                   (p.B3G_DOWN_ARROW,p.B3G_UP_ARROW),
                                                   (p.B3G_PAGE_DOWN,p.B3G_PAGE_UP))):
            if abs(desired[axis]-wb[axis])<.002:
                continue
            key=positive if effort[axis]>0 else negative
            for i in attitude_rcs_indices(lander,{key:p.KEY_IS_DOWN}):
                result[i]=max(result[i],float(abs(effort[axis])))
        return result

def windows_caps_trigger(previous_down):
    """Fallback when Bullet's keyboard backend does not forward CapsLock."""
    if sys.platform!='win32':
        return False,False
    import ctypes
    import os
    user32=ctypes.windll.user32
    user32.GetForegroundWindow.restype=ctypes.c_void_p
    user32.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    process=ctypes.c_ulong()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(),ctypes.byref(process))
    if process.value!=os.getpid():
        return False,False
    raw=user32.GetAsyncKeyState(20)
    down=bool(raw&0x8000)
    return bool((down and not previous_down) or (raw&1)),down
