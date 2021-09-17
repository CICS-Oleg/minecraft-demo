import math
from time import sleep
from tagilmo.utils.malmo_wrapper import MalmoConnector, RobustObserver
import tagilmo.utils.mission_builder as mb

# This script shows a relatively complex behavior of gathering resources
# for an iron pickaxe. It includes searchng for logs, mining stones, etc.
# There are many heurisics and many things that can go wrong,
# so the final result will not be achieved. And this is OK.
#
# The example is intented to show the capabilities and limitations of
# imperative scripts and hand-coding. Failer can be due to the lack
# of robustness and flexibility of:
# * local skills (e.g. the agent can start mining a shaft in the direction of lava)
# * high-level plan (the agent can run out of sticks, when the plan assumes it has enough)
# The longer the plan, the more things can go wrong.
# It is instructive to examine failure cases.

passableBlocks = ['air', 'water', 'lava', 'double_plant', 'tallgrass', 'reeds', 'red_flower', 'yellow_flower']


# ============== some helper functions ==============

def normAngle(angle):
    while (angle < -math.pi): angle += 2 * math.pi
    while (angle > math.pi): angle -= 2 * math.pi
    return angle

def stopMove(rob):
    rob.sendCommand("move 0")
    rob.sendCommand("turn 0")
    rob.sendCommand("pitch 0")
    rob.sendCommand("jump 0")
    rob.sendCommand("strafe 0")

def nearestFromGrid(rob, obj):
    grid = rob.waitNotNoneObserve('getNearGrid')
    pos  = rob.waitNotNoneObserve('getAgentPos')
    d2 = 10000
    target = None
    for i in range(len(grid)):
        if grid[i] != obj: continue
        [x, y, z] = rob.mc.gridIndexToPos(i)
        d2c = x * x + y * y + z * z
        if d2c < d2:
            d2 = d2c
            # target = rob.gridIndexToAbsPos(i)
            target = [x + pos[0], y + pos[1], z + pos[2]]
    return target

def nearestFromEntities(rob, obj):
    ent = rob.waitNotNoneObserve('getNearEntities')
    pos = rob.waitNotNoneObserve('getAgentPos')
    d2 = 10000
    target = None
    for e in ent:
        if e['name'] != obj: continue
        [x, y, z] = [e['x'], e['y'], e['z']]
        if abs(y - pos[1]) > 1: continue
        d2c = (x - pos[0]) * (x - pos[0]) + (y - pos[1]) * (y - pos[1]) + (z - pos[2]) * (z - pos[2])
        if d2c < d2:
            d2 = d2c
            target = [x, y, z]
    return target


# ============== some hand-coded skills ==============

# This function is executed to run to a visible object,
# but it doesn't check if the path is safe
def runStraight(rob, dist):
    start = rob.waitNotNoneObserve('getAgentPos')
    rob.sendCommand("move 1")
    for t in range(2+int(dist*5)):
        sleep(0.1)
        rob.observeProcCached()
        pos = rob.getCachedObserve('getAgentPos')
        if pos is None:
            continue
        if dist * dist < (pos[0] - start[0]) * (pos[0] - start[0]) + (pos[2] - start[2]) * (pos[2] - start[2]):
            break
        los = rob.getCachedObserve('getLineOfSights')
        if los is not None and los['distance'] < 0.5 and \
           not los['distance'] in passableBlocks and \
           not los['type'] in passableBlocks:
            break
    rob.sendCommand("move 0")

# Just look at a specified direction
def lookDir(rob, pitch, yaw):
    for t in range(3000):
        sleep(0.02) # wait for action
        aPos = rob.waitNotNoneObserve('getAgentPos')
        dPitch = normAngle(pitch - aPos[3]*math.pi/180.)
        dYaw = normAngle(yaw - aPos[4]*math.pi/180.)
        if abs(dPitch)<0.02 and abs(dYaw)<0.02: break
        rob.sendCommand("turn " + str(dYaw*0.4))
        rob.sendCommand("pitch " + str(dPitch*0.4))
    rob.sendCommand("turn 0")
    rob.sendCommand("pitch 0")

# Look at a specified location
def lookAt(rob, pos):
    for t in range(3000):
        sleep(0.02)
        aPos = rob.waitNotNoneObserve('getAgentPos')
        [pitch, yaw] = rob.dirToPos(pos)
        pitch = normAngle(pitch - aPos[3]*math.pi/180.)
        yaw = normAngle(yaw - aPos[4]*math.pi/180.)
        if abs(pitch)<0.02 and abs(yaw)<0.02: break
        rob.sendCommand("turn " + str(yaw*0.4))
        rob.sendCommand("pitch " + str(pitch*0.4))
    rob.sendCommand("turn 0")
    rob.sendCommand("pitch 0")
    return math.sqrt((aPos[0] - pos[0]) * (aPos[0] - pos[0]) + (aPos[2] - pos[2]) * (aPos[2] - pos[2]))

def strafeCenterX(rob):
    rob.sendCommand('strafe 0.1')
    for t in range(200):
        sleep(0.02)
        aPos = rob.waitNotNoneObserve('getAgentPos')
        if int(abs(aPos[0])*10+0.5)%10==5:
            break
    stopMove(rob)
    

# A simplistic search behavior
# Note that we don't use video input and rely on a small Grid and Ray,
# so our agent can miss objects visible by human
def search4blocks(rob, blocks):
    for t in range(3000):
        sleep(0.02) # for action execution - not observations
        grid = rob.waitNotNoneObserve('getNearGrid')
        for i in range(len(grid)):
            if grid[i] in blocks:
                stopMove(rob)
                return [grid[i]] + rob.gridIndexToAbsPos(i)
        los = rob.getCachedObserve('getLineOfSights')
        if los is not None and los['type'] in blocks:
            stopMove(rob)
            return [los['type'], los['x'], los['y'], los['z']]
        gridSlice = rob.gridInYaw()
        ground = gridSlice[(len(gridSlice) - 1) // 2 - 1]
        solid = all([not (b in passableBlocks) for b in ground])
        wayLv0 = gridSlice[(len(gridSlice) - 1) // 2]
        wayLv1 = gridSlice[(len(gridSlice) - 1) // 2 + 1]
        passWay = all([b in passableBlocks for b in wayLv0]) and all([b in passableBlocks for b in wayLv1])
        turnVel = 0.25 * math.sin(t * 0.05)
        if not (passWay and solid):
            turnVel -= 1
        pitchVel = -0.015 * math.cos(t * 0.03)
        rob.sendCommand("move 1")
        rob.sendCommand("turn " + str(turnVel))
        rob.sendCommand("pitch " + str(pitchVel))
    stopMove(rob)
    return None

# Just attacking while the current block is not destroyed
# assuming nothing else happens
def mineAtSight(rob):
    sleep(0.1)
    rob.observeProcCached()
    los = rob.getCachedObserve('getLineOfSights')
    if los is None or los['type'] is None or not los['inRange']:
        return False
    dist = los['distance']
    obj = los['type']
    rob.sendCommand('attack 1')
    for t in range(100):
        los = rob.getCachedObserve('getLineOfSights')
        if los is None or los['type'] is None or \
           abs(dist - los['distance']) > 0.01 or obj != los['type']:
            rob.sendCommand('attack 0')
            return True
        sleep(0.1)
        rob.observeProcCached()
    rob.sendCommand('attack 0')
    return False

# A skill to choose a tool for mining (in the context of the current example)
def chooseTool(rob):
    los = rob.getCachedObserve('getLineOfSights')
    if los is None:
        return
    wooden_pickaxe = rob.filterInventoryItem('wooden_pickaxe')
    if wooden_pickaxe and wooden_pickaxe[0]['index'] != 0:
        rob.sendCommand('swapInventoryItems 0 ' + str(wooden_pickaxe[0]['index']))
    stone_pickaxe = rob.filterInventoryItem('stone_pickaxe')
    if stone_pickaxe and stone_pickaxe[0]['index'] != 1:
        rob.sendCommand('swapInventoryItems 1 ' + str(stone_pickaxe[0]['index']))
    if los['type'] in ['dirt', 'grass']:
        rob.sendCommand('hotbar.9 1')
        rob.sendCommand('hotbar.9 0')
    elif los['type'] in ['iron_ore']:
        rob.sendCommand('hotbar.2 1')
        rob.sendCommand('hotbar.2 0')
    else: # 'stone', etc.
        if wooden_pickaxe:
            rob.sendCommand('hotbar.1 1')
            rob.sendCommand('hotbar.1 0')
        else:
            rob.sendCommand('hotbar.2 1')
            rob.sendCommand('hotbar.2 0')
    
# Mine not just one block, but everything in range
def mineWhileInRange(rob):
    rob.sendCommand('attack 1')
    rob.observeProcCached()
    while rob.getCachedObserve('getLineOfSights') is None or rob.getCachedObserve('getLineOfSights', 'inRange'):
        sleep(0.02)
        rob.observeProcCached()
        chooseTool(rob)
    rob.sendCommand('attack 0')

# A higher-level skill for getting sticks
def getSticks(rob):
    # repeat 3 times, because the initial target can be wrong due to tallgrass
    # or imprecise direction to a distant tree
    for i in range(3):
        target = search4blocks(rob, ['log', 'leaves'])
        dist = lookAt(rob, target[1:4])
        runStraight(rob, dist)

    target = nearestFromGrid(rob, 'log')
    while target is not None:
        lookAt(rob, target)
        if not mineAtSight(rob):
            break
        target = nearestFromEntities(rob, 'log')
        if target is not None:
            runStraight(rob, lookAt(rob, target))
        target = nearestFromGrid(rob, 'log')

    while rob.filterInventoryItem('log') != []: # [] != None as well
        rob.craft('planks')

    rob.craft('stick')

# A very simple skill for leaving a flat shaft mined in a certain direction
def leaveShaft(rob):
    lookDir(rob, 0, math.pi)
    rob.sendCommand('move 1')
    rob.sendCommand('jump 1')
    while rob.waitNotNoneObserve('getAgentPos')[1] < 30.:
        sleep(0.1)
    stopMove(rob)

# Making a shaft in a certain direction
def mineStone(rob):
    lookDir(rob, math.pi/4, 0.0)
    strafeCenterX(rob)
    while True:
        mineWhileInRange(rob)
        runStraight(rob, 1)
        stones = rob.filterInventoryItem('cobblestone')
        if stones != None and stones != [] and stones[0]['quantity'] >= 3: break

# The skill that will most likely fail: it's not that easy to find iron ore and coal
# without even looking around
def mineIron(rob):
    strafeCenterX(rob)
    while rob.waitNotNoneObserve('getAgentPos')[1] > 22.:
        mineWhileInRange(rob)
        runStraight(rob, 1)
    rob.sendCommand('move 1')
    rob.sendCommand('attack 1')
    while True:
        sleep(0.1)
        rob.observeProcCached()
        chooseTool(rob)
        iron_ore = rob.filterInventoryItem('iron_ore')
        coal = rob.filterInventoryItem('coal')
        if iron_ore != None and iron_ore != [] and iron_ore[0]['quantity'] >= 3 and \
           coal != None and coal != [] and coal[0]['quantity'] >= 3:
               rob.craft('iron_ingot')
               rob.craft('iron_ingot')
               rob.craft('iron_ingot')
               rob.craft('iron_pickaxe')
               break
        pickaxe = rob.filterInventoryItem('stone_pickaxe')
        if pickaxe == []:
            break


miss = mb.MissionXML()
miss.setWorld(mb.flatworld("3;7,25*1,3*3,2;1;stronghold,biome_1,village,decoration,dungeon,lake,mineshaft,lava_lake", forceReset="true"))
miss.serverSection.initial_conditions.allowedmobs = "Pig Sheep Cow Chicken Ozelot Rabbit Villager"
mc = MalmoConnector(miss)
mc.safeStart()
rob = RobustObserver(mc)
# fixing bug with falling through while reconnecting
sleep(2)
rob.sendCommand("jump 1")
sleep(0.1)
rob.sendCommand("jump 0")


lookDir(rob, 0, 0)

getSticks(rob)

rob.craft('wooden_pickaxe')
pickaxe = rob.filterInventoryItem('wooden_pickaxe')
if pickaxe == []:
    print("Failed")
    exit()

# put pickaxe into inventory_0 == hotbar.1 slot
rob.sendCommand('swapInventoryItems 0 ' + str(pickaxe[0]['index']))

mineStone(rob)

rob.craft('stone_pickaxe')
pickaxe = rob.filterInventoryItem('stone_pickaxe')
# put pickaxe into inventory_1 == hotbar.2 slot
rob.sendCommand('swapInventoryItems 1 ' + str(pickaxe[0]['index']))

#climbing up
leaveShaft(rob)

rob.sendCommand('move 1')
rob.sendCommand('attack 1')
sleep(3)
stopMove(rob)
getSticks(rob)

lookDir(rob, math.pi/4, 0.0)
mineIron(rob)
leaveShaft(rob)

if not rob.filterInventoryItem('iron_pickaxe'):
    lookDir(rob, math.pi/4, math.pi)
    mineIron(rob)
    leaveShaft(rob)
