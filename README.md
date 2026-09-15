# Menu Generator

Menu are stored in [cooklang](https://cooklang.org/) and this repo contains scripts to help
you automatically genearte menu for next week.

## How to run

```
./gen
```

Will generate menu for next week. It will generate a `.menu` files that written in cooklang and a `.md` file
that contains a shopping list and link to the source of menu.

## Config what to generate

All the recipes have some tags, you can filter all the menus by tag. Change `config.toml` to control what will be
generated.


```toml
["减肥餐-晚餐"]
tags = ["减肥餐"]

["减肥餐-午餐"]
tags = ["减肥餐"]
# Only generate this for following days.
days = [0, 4, 5, 6]

["宝宝餐-主食"]
tags = ["宝宝餐", "主食"]


["宝宝餐-肉菜"]
tags = ["宝宝餐", "肉菜"]

["宝宝餐-素菜"]
tags = ["宝宝餐", "素菜"]
```

## Future Plans

- [ ] Nutrition geneartion
- [ ] More baby/diet menus
