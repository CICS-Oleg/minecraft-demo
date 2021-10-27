

s = """
97, grass
50, dirt
68, fire
66, white_flower/azure_bluet
22, tallgrass
69, yellow_flower/dandelion
67, red_flower/oxeye_daisy
86, vine
122, log/oak
121, log/birch
115, leaves/birch
120, leaves/oak
35, double_plant/sunflower
14, stone/andesite
46, stone/granite
98, gravel
102, water
0, flowing_water
175, duck
27, sunflower
96, gold_ore
6, stone/stone
30, stone/diorite
117, sand
114, lava"""

segment_mapping = dict()

for line in s.split('\n'):
    if line.strip():
        code, name = line.split(',')
        segment_mapping[int(code.strip())] = name.strip()
