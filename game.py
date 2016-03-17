from random import randint
from time import sleep
from itertools import chain
from shutil import get_terminal_size
import re
import json
global empty, miss, ship, hit
empty, miss, ship, hit = 0, 1, 2, 3
global up, right, down, left
up, right, down, left = 0, 1, 2, 3
global player1, player2
player1, player2 = 0, 1
seperator = lambda txt:re.split(r'[, .|]+', txt)
xFilter = (lambda txt:re.fullmatch(r'[A-Z]+', txt, re.I), lambda txt: txt.upper())
yFilter = (lambda txt:re.fullmatch(r'\d+', txt), lambda txt: int(txt))
dirFilter = (lambda txt:re.fullmatch(r'(?:[urdl]|up|right|down|left)', txt, re.I), lambda txt: txt.upper()[0])
screenWidth, screenHeight = get_terminal_size()
examples = {'ship':("A 0 Down", "A, 0, D", "a, 0 DoWN"), 'attack':("A, 0", "0, a", "a 0")}
refresh, check = True, 'strict'
global gridSize, shipName, shipLength, colors
try:
	for configurable in ('wasteTurns', 'gridSize', 'shipLength', 'shipName', 'colors'):
		locals()[configurable] = json.load(open("config.json"))[configurable]
except TypeError:
	raise Exception("Invalid config.json")
if(gridSize < 1 or len(shipLength) < 1 or len(shipName) < 1 or min(shipLength) < 1 or max(shipLength) > gridSize or sum(shipLength) > gridSize ** 2):
	raise Exception("Invalid values in config.json")
for key, value in colors.items():
	colors[key] = '\033[3{}m'.format(('black', 'red', 'green', 'yellow', 'blue', 'purple', 'cyan', 'white').index(value))
global grid, ships, reset, cell
grid = range(gridSize)
ships = tuple(zip(shipName, shipLength))
reset = '\033[0m'
cell = {empty:colors['empty'] + '~', miss:colors['miss'] + 'O', ship:colors['ship'] + '#', hit:colors['hit'] + 'X'}
global queueGrid, defenseGrid, shipsGrid
defenseGrid = [[[0 for y in grid] for x in grid] for team in range(2)]
shipsGrid, queueGrid = [[], []], [[], []]
history = [('War', 'Declared', colors['success'])]
global printLoc
printLoc = lambda text, x, y:print('\033[{y};{x}H{text}'.format(y = y, x = x,text = text)+reset)
practicalX = lambda coord: sum([(([chr(i + 65) for i in range(26)].index(val.upper()) + 1) * 26 ** i) for i, val in enumerate(reversed(coord))])-1
def round(num: float):
	adder = 0
	for digit in reversed(str(num)[str(num).index('.') + 1:]):
		adder = int(int(digit) + adder >= 5)
	return(int(str(num)[:str(num).index('.')]) + adder)
def updateScreen():
	leftGrid, rightGrid, leftTitle, rightTitle = defenseGrid[player2], defenseGrid[player1], "Enemy Fleet", "Your Fleet"
	title = "=== TimoTree Battleship ==="
	ruler = ' '.join([chr(i + 65) for i in range(gridSize)])
	legend = {'title':'Legend:', empty:'Empty', miss:'Miss', ship:'Ship', hit:'Hit'}
	histName = 'History'
	global screenWidth, screenHeight, history, refresh
	b4Width, b4Height, screenWidth, screenHeight = screenWidth, screenHeight, *get_terminal_size()
	if(screenWidth<72 or screenHeight<24 or b4Width != screenWidth or b4Height != screenHeight):
		if(screenWidth<72 or screenHeight<24):
			printLoc("Please enlarge your terminal", 0, 0)
		refresh = True
		while(screenWidth<72 or screenHeight<24 or b4Width != screenWidth or b4Height != screenHeight):
			b4Width, b4Height, screenWidth, screenHeight = screenWidth, screenHeight, *get_terminal_size()
			sleep(0.1)
	align = lambda text, alignment, hidden = 0:round(hidden + {'l':screenWidth / 4, 'm':screenWidth / 2, 'r':screenWidth * 3 / 4}[alignment] - (len(text) / 2))
	leftX, legendX, rightX = screenWidth // 4 - (gridSize + 1), align(legend['title'], 'm') - 1, screenWidth * 3 // 4 - (gridSize + 1)
	if(refresh):
		from os import name, system
		print('\033[s\033[2J')
		system('cls' if name == 'nt' else 'clear')
		print('\033[u')
		printLoc(colors['interface'] + title, align(title, 'm'), 2)
		printLoc(colors['interface'] + leftTitle, align(leftTitle, 'l') - 1, 4)
		printLoc(colors['interface'] + rightTitle, align(rightTitle, 'r'), 4)
		printLoc(colors['interface'] + ruler, leftX+2, 6)
		printLoc(colors['interface'] + ruler, rightX+2, 6)
		printLoc(colors['interface'] + legend['title'], legendX + 1, 7)
		for i, cellType in enumerate(cell):
			printLoc(cell[cellType] + " - " + legend[cellType], legendX, i + 8)
	for y in grid:
		printLoc(colors['interface'] + str(y), leftX, 7+y)
		printLoc(colors['interface'] + str(y), rightX, 7+y)
		for x in grid:
			printLoc(cell[{ship:empty}.get(leftGrid[x][y], leftGrid[x][y])], leftX+(x+1) * 2, 7+y)
			printLoc(cell[rightGrid[x][y]], rightX+(x+1) * 2, 7+y)
	printLoc('\033[J' + colors['prompt'] + histName, align(histName, 'm'), gridSize + 11)
	for place, action, color, y in zip(*zip(*reversed(history)), range(gridSize + 12, screenHeight)):
		message = '{}: {}'.format(place, action)
		printLoc(color + message, align(message, 'm'), y)
	refresh = False
def getInput(prompt, example = None, queue = None, hidden = 0):
	global examples, inputMessage
	printLoc(inputMessage[1] + '{}.'.format(inputMessage[0].capitalize()), 0, gridSize + 8)
	if(example in examples):
		printLoc(colors['prompt'] + 'Example input{1}: ({0})'.format(' | '.join(examples[example]), 's'[:len(example) - 1]), 0, gridSize + 10)
	if(queue):
		printLoc('\033[2K' + colors['prompt'] + 'Suggested move{1}: {0}'.format(', '.join(['{} {}'.format(chr(x + 65), y) for x, y in queue[-3:]]), 's'[:len(queue)]), 0, gridSize + 10)
	answer = input(colors['prompt'] + '\033[{y};0H{}{}: '.format(prompt, reset, y = gridSize + 9))
	printLoc('\033[2K\n' * 3, 0, gridSize + 8)
	return answer.strip()
def parseInput(text, preparation, *filters):
	from itertools import permutations
	prepared = preparation(text)
	for inputLength in range(len(filters), len(prepared)+1):
		for combo in permutations(prepared[:inputLength]):
			match = []
			for element, Filter in zip(combo, filters):
				match.append(Filter[1](element) if(Filter[0](element)) else None)
			if(None not in match):
				return match
	return False
def offensiveTurn(player, x = 0, y = 0):
	enemy = int(not(player))
	if(player == player2):
		if(queueGrid[player]):
			x, y = queueGrid[player][randint(0, len(queueGrid[player]) - 1)]
		else:
			global check
			while(check):
				queue, invalids = [], []
				for y in grid:
					for x in grid:
						if(defenseGrid[enemy][x][y] % 2 == 0):
							queue.append((x, y))
						else:
							invalids.append((x, y))
				for x, y in {'strict':invalids, 'casual':queue}[check]:
					for offset in range(1, min([shipLength[i] for i, shipList in enumerate(shipsGrid[enemy]) if len(shipList) > 0])):
						if(check == 'strict'):
							for checkX, checkY in ((x - offset, y), (x + offset, y), (x, y - offset), (x, y + offset)):
								if((checkX, checkY) in queue):
									queue.remove((checkX, checkY))
						elif(check == 'casual'):
							for checkX, checkY in ((x - offset, y), (x + offset, y), (x, y - offset), (x, y + offset)):
								if(defenseGrid[enemy][checkX][checkY] != miss):
									break
							else:
								queue.remove((x, y))
				if(queue):
					x, y = queue[0]
					break
				else:
					check = ('strict', 'casual', None)[('strict', 'casual', None).index(check) + 1]
			else:
				x, y = (randint(0, gridSize - 1), randint(0, gridSize - 1))
	while((x, y) in queueGrid[player]):
		queueGrid[player].remove((x, y))
	if(x not in grid or y not in grid):
		return ('out', x, y)
	try:
		defenseGrid[enemy][x][y] = {empty:miss,ship:hit}[defenseGrid[enemy][x][y]]
	except KeyError:
		return ('wasted', x, y)
	if(defenseGrid[enemy][x][y] == miss):
		return ('miss', x, y)
	elif(defenseGrid[enemy][x][y] == hit):
		sunk = None
		for i, shipCells in enumerate(shipsGrid[enemy]):
			if((x, y) in shipCells):
				shipCells.remove((x, y))
				if(len(shipCells) == 0):
					sunk = i
				break
		for queueX in (x - 1, x + 1):
			for queueY in (y - 1, y + 1):
				if(queueX in grid and queueY in grid and (queueX, queueY) in queueGrid[player]):
					queueGrid[player].remove((queueX, queueY))
		if(sunk != None):
			return (sunk, x, y)
		for queueX, queueY in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
			if(queueX in grid and queueY in grid and (queueX, queueY) not in queueGrid[player] and defenseGrid[enemy][queueX][queueY] % 2 == 0):
				queueGrid[player].append((queueX, queueY))
		return ('hit', x, y)
def count(array, value, boolean = False):
	result = array.count(value)
	if(result > 0 and boolean):
		return(True)
	for element in array:
		if(type(element) == list):
			result += count(element, value, maximum)
	return result
def addShip(x, y, direction, length, player):
	placementQueue = []
	directions = ('L', 'U', 'R', 'D') if type(direction) == str else (left, up, right, down)
	step, axis = dict(zip(directions, ((-1, 'X'), (-1, 'Y'), (1, 'X'), (1, 'Y'))))[direction]
	xLength, yLength, xStep, yStep = [1, step * length, 1, step] if axis == 'Y' else [step * length, 1, step, 1]
	for xIter in range(x, x+xLength, xStep):
		for yIter in range(y, y+yLength, yStep):
			if(xIter in grid and yIter in grid):
				if(defenseGrid[player][xIter][yIter] == empty):
					placementQueue.append((str(xIter), str(yIter)))
				else:
					return 'occupied'
			else:
				return 'out'
	shipsGrid[player].append([])
	for shipLoc in placementQueue:
		x, y = int(shipLoc[0]), int(shipLoc[1])
		defenseGrid[player][x][y] = ship
		shipsGrid[player][-1].append((x, y))
	return 'success'
inputMessage = ("game started", colors['success'])
while(len(shipsGrid[player1]) < len(ships)):
	updateScreen()
	shipInfo = ships[len(shipsGrid[player1])]
	result = getInput("Place your {}{preview}".format(shipInfo[0], preview = (' '+cell[ship]) * shipInfo[1]), 'ship', hidden = 5 * shipInfo[1])
	inputMessage = ("filling board", colors['success'])
	if(result == 'dev' and len(shipsGrid[player1]) == 0):
		for i, y in enumerate(range(0, gridSize, 2)):
			addShip(0, y, right, shipLength[i], player1)
	else:
		result = parseInput(result, seperator, xFilter, yFilter, dirFilter)
		if(result):
			prettyX, shipY, shipDir = result
			shipX = practicalX(prettyX)
			shipMessage = addShip(shipX, shipY, shipDir, shipInfo[1], player1)
			if(shipMessage == 'success'):
				history.append((prettyX + str(shipY), 'Ship Placed', colors['ship']))
			elif(shipMessage == 'occupied'):
				inputMessage = ("location already filled", colors['fail'])
			elif(shipMessage == 'out'):
				inputMessage = ("location out of bounds", colors['fail'])
		else:
			inputMessage = ("invalid ship location", colors['fail'])
while(len(shipsGrid[player2]) < len(ships)):
	shipInfo = ships[len(shipsGrid[player2])]
	shipX, shipY = randint(min(grid), max(grid)), randint(min(grid), max(grid))
	direction = randint(0, 3)
	addShip(shipX, shipY, direction, shipInfo[1], player2)
turnCount = 0
inputMessage = ("you are now attacking", colors['success'])
history = [("Ships", 'Placed', colors['ship'])]
while(True):
	updateScreen()
	if(turnCount % 2 == 0):
		status, player, enemy = 'won', player1, player2
		result = parseInput(getInput("Attack a cell", 'attack', queueGrid[player]), seperator, xFilter, yFilter)
		inputMessage = ("it is your turn", colors['success'])
		if(result):
			prettyX, attackY = result
			attackX = practicalX(prettyX)
			turnMessage = offensiveTurn(player1, attackX, attackY)[0]
		else:
			inputMessage = ("invalid input", colors['fail'])
			continue
	else:
		sleep(0.75)
		status, player, enemy = 'lost', player2, player1
		turnMessage, attackX, attackY = offensiveTurn(player2)
		prettyX = chr(attackX+65)
	if(turnMessage == 'wasted'):
		inputMessage = ("cell already attacked", colors['fail'])
	if(turnMessage == 'out'):
		inputMessage = ("location out of bounds", colors['fail'])
	elif(not(turnMessage == 'wasted') or wasteTurns):
		turnCount += 1
		if(type(turnMessage) == int):
			updateScreen()
			history.append((prettyX + str(attackY), "Sunk '{}'".format(ships[turnMessage][0].title()), colors['ship']))
			if(len(list(chain.from_iterable(shipsGrid[enemy]))) == 0):
				input('\033[17;0H\033[J\n' + colors['interface'] + "You {} in {turns} turns!".format(status, turns = turnCount // 2).center(screenWidth - 1) + reset + '\n')
				break
		else:
			history.append((prettyX + str(attackY), turnMessage.capitalize(), colors['empty'] if turnMessage == 'wasted' else colors[turnMessage]))
