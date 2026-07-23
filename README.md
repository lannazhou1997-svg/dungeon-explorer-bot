# 地下城探索 Bot

一个运行在 Discord 中的轻量 Roguelike 地下城游戏原型。

## 当前玩法

- 地下城共 100 层，每层需要完成随机步数的探索。
- 普通层由小 Boss 守关，第 5、10、15……100 层由大 Boss 守关。
- 探索途中可能遇到怪物、商店、宝箱、宝箱怪、陷阱、恢复事件或空房间。
- 体力用于承受伤害，魔力用于技能，精力用于探索和开启宝箱。
- 死亡后等级、经验、层数和普通道具重置；装备及剩余货币保留。
- 玩家面板使用 Discord 横向字段展示体力、魔力与精力。

## 启动

1. 安装 Python 3.11 或更高版本。
2. 安装依赖：`pip install -r requirements.txt`
3. 将 `.env.example` 复制为 `.env`，填写 `DISCORD_TOKEN`。
4. 运行：`python bot.py`
5. 在 Discord 中输入 `/地下城`。

服务器管理员还可以使用 `/地下城测试`，从下拉菜单中指定普通怪物、宝箱、
伪装中的宝箱怪、泉水、旅行商人、陷阱、小 Boss 或大 Boss，方便逐项检查面板。

如果填写了 `TEST_GUILD_ID`，指令会优先同步到该测试服务器，通常几秒内可见；不填写则注册为全局指令。填写 `DUNGEON_CHANNEL_ID` 后，地下城指令只能在指定文字频道使用。

## 在 GitHub Codespaces 运行

1. 在仓库页面点击 **Code → Codespaces → Create codespace on main**。
2. 在 Codespaces 终端执行：

   ```bash
   cp .env.example .env
   nano .env
   ```

3. 在 `.env` 中填写 Bot Token、测试服务器 ID 和地下城频道 ID，保存后执行：

   ```bash
   pip install -r requirements.txt
   python bot.py
   ```

4. 看到 `已登录：机器人名称` 后，前往指定 Discord 频道输入 `/地下城`。

`.env` 已被 Git 忽略，不要将 Token 提交到仓库。Codespace 终端需要保持运行；停止 Codespace 后 Bot 会离线。

## 当前版本说明

商店和装备宝箱已作为事件入口展示，购买与装备抽取会在下一阶段接入。项目使用独立 SQLite 数据库，不会读取或修改现有签到 Bot。
