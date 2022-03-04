import minecraft_data
# to install minecraft_data package:
# pip install minecraft_data

# Java edition minecraft-data
mcd = minecraft_data("1.11.2")


class MCDataWrapper:

    def __init__(self, mcd):
        self.mcd = mcd

    def _getBlockIdByName(self, name):
        return mcd.find_item_or_block(name)['id']

    def _processGridItems(self, grid_item):
        if isinstance(grid_item, dict):
            return grid_item['id']
        elif grid_item is None:
            return -1
        else:
            return grid_item

    def _inclusionCheck(self, item, recipe):
        if 'inShape' in recipe:
            grid = recipe['inShape']
            first_or_default = next((j for row in grid for j in row if self._processGridItems(j)==item), None)
            return False if first_or_default is None else True
        else:
            grid = recipe['ingredients']
            first_or_default = next((j for j in grid if self._processGridItems(j) == item), None)
            return False if first_or_default is None else True

    def getItemOrBlockRecipeInclusions(self, name):
        item = self._getBlockIdByName(name)
        result = [recipe for recipe_list in self.mcd.recipes.values() for recipe in recipe_list if self._inclusionCheck(item,
                                                                                                               recipe)]
        return result


mcdata_wrp = MCDataWrapper(mcd)

print(len(mcdata_wrp.getItemOrBlockRecipeInclusions('stone')))
print(mcdata_wrp.getItemOrBlockRecipeInclusions('stone'))
# print(mcd.version)
#
# print(mcd.find_item_or_block(70))

# print(mcd.find_item_or_block('stone'))
#
# print(mcd.recipes['5'])
