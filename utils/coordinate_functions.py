import numpy as np
from numpy.linalg import norm
import math 
import sys

def frenet2cart(traj, ref):

    return 0

def cart2frenet(traj, ref):
    '''
    traj = np array of size [T,2]
    ref = np array of size [L,2]
    '''
    #print('CART2FRENET')
    L = ref.shape[0]
    T = traj.shape[0]
    gamma = np.zeros((L))
    for i in range(L-1):
        gamma[i] = norm(ref[i+1]-ref[i])
    gamma[L-1] = gamma[L-2]
    gamma = np.cumsum(gamma)
    ref_frenet = np.zeros((L, 2))
    ref_frenet[:,0] = gamma
    traj_frenet = np.zeros((T, 2))
    for i in range(T):
        min2itr = np.argpartition(norm(ref-traj[i], axis=1), 3)[0:2]
        it = np.min(min2itr)
        it1 = np.max(min2itr)
        traj_frenet[i,0] =  gamma[it] + norm(np.dot(ref[it1]-ref[it], ref[it]-traj[i]))/norm(ref[it1]-ref[it])
        traj_frenet[i,1] = norm(np.cross(ref[it1]-ref[it], ref[it]-traj[i]))/norm(ref[it1]-ref[it])
        #print('it:{}, it1:{}'.format(it,it1))
    return traj_frenet, ref_frenet


def frenet2cart( traj, ref): #assumption: traj y>ref y , ref is in cart coordinate equally it means thetha>0
        #print('FRENET2CART')
        epsilon=sys.float_info.epsilon
        L = ref.shape[0]
        T = traj.shape[0]
        cart_traj = np.zeros_like(traj)
        gamma = np.zeros((L))
        for i in range(L-1):
            gamma[i] = norm(ref[i+1]-ref[i])
        gamma[L-1] = gamma[L-2]
        gamma = np.cumsum(gamma)
        traj_cart = np.zeros((T,2))
        for i in range(T):
            it2 = np.nonzero(gamma>traj[i,0])[0][0]
            it1 = it2-1
            assert(it1>=0)             

            thetha1 = np.arctan((ref[it2,1]-ref[it1,1])/(ref[it2,0]-ref[it1,0]+epsilon))
            
            thetha = np.arctan((np.abs(traj[i,1]))/(np.abs(traj[i,0]- gamma[it1])+epsilon))
            #print('log')
            #print(traj[i,1])
            #print(traj[i,0])
            #print(it1)
            #print(thetha)
            #if thetha < np.abs(thetha1):
            #    thetha *= -1
            thetha_cart = thetha1+thetha
            dist2origin = np.sqrt(np.power(traj[i,1], 2) + np.power((traj[i,0]- gamma[it1]), 2))
            #assert(np.sin(thetha_cart)>0)
            #assert(np.cos(thetha_cart)>0)
            cart_traj[i,0] = dist2origin * np.cos(thetha_cart) + ref[it1, 0]
            cart_traj[i,1] = dist2origin * np.sin(thetha_cart) + ref[it1, 1]
            #print('it1:{}, it2:{}, theta:{}, theta1:{},{},{},{}'.format(it1,it2,thetha*180/np.pi,thetha1*180/np.pi, (np.abs(traj[i,1]))/(np.abs(traj[i,0]- gamma[it1])+epsilon),np.abs(traj[i,1]),thetha_cart*180/np.pi) )
        return cart_traj

def asRadians(degrees):
    return degrees * math.pi / 180

def longlat2xy(data_coordinates, null_coordinates):
    """ Calculates X and Y distances in meters.
    """
    (data_long, data_lat) = data_coordinates
    (null_long, null_lat) = null_coordinates
    deltaLatitude = data_lat - null_lat
    deltaLongitude = data_long - null_long
    latitudeCircumference = 40075160 * math.cos(asRadians(null_lat))
    resultX = deltaLongitude * latitudeCircumference / 360
    resultY = deltaLatitude * 40008000 / 360
    
    return (resultX, resultY) 