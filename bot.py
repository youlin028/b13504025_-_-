import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import json
import os
import calendar

# 初始化機器人
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 檔案名稱 (用來儲存每日計畫的資料)
DATA_FILE = "daily_plans.json"

# 初始化資料檔案
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as file:
        json.dump({}, file)

# 讀取資料
def load_data():
    with open(DATA_FILE, "r") as file:
        return json.load(file)

# 保存資料
def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# 指令：初始化每日計畫表
@bot.command(name="start_plan")
async def start_plan(ctx, date: str):
    """
    初始化一個新的每日計畫表。
    使用格式: !start_plan YYYY-MM-DD
    """
    try:
        # 驗證日期格式
        datetime.strptime(date, "%Y-%m-%d")
        data = load_data()
        
        if date in data:  # 如果當天已存在資料
            await ctx.send(f"📅 {date} 的計畫表已經存在！您可以使用 `!add_task` 添加任務。")
            return

        # 初始化當日計畫表
        data[date] = {f"{i}-{i+2}時": "無任務" for i in range(8, 24, 2)}
        save_data(data)
        await ctx.send(f"✅ 已成功建立 {date} 的每日計畫表！")
    except ValueError:
        await ctx.send("❌ 日期格式錯誤！請使用 YYYY-MM-DD 格式。")

# 指令：輸入每日代辦事項
@bot.command(name="add_task")
async def add_task(ctx, date: str, time_period: str, *, task: str):
    """
    在指定時段輸入任務。
    使用格式: !add_task YYYY-MM-DD 8-10時 任務內容
    """
    try:
        data = load_data()

        if date not in data:  # 驗證日期是否存在
            await ctx.send(f"❌ {date} 尚未建立計畫表！請先使用 `!start_plan {date}` 初始化。")
            return

        if time_period not in data[date]:  # 驗證時段是否正確
            await ctx.send(f"❌ 時段 {time_period} 無效！請使用這些時段之一：{', '.join(data[date].keys())}")
            return

        # 更新任務
        data[date][time_period] = task
        save_data(data)
        await ctx.send(f"✅ 已成功在 {date} 的 {time_period} 輸入任務：{task}")
    except Exception as e:
        await ctx.send(f"⚠️ 發生錯誤：{str(e)}")

# 指令：查看每日計畫表
@bot.command(name="view_plan")
async def view_plan(ctx, date: str):
    """
    查看某天的計畫表，並以嵌入消息形式呈現。
    使用格式: !view_plan YYYY-MM-DD
    """
    try:
        data = load_data()

        if date not in data:  # 驗證日期是否存在
            await ctx.send(f"❌ {date} 尚未建立計畫表！請先使用 `!start_plan {date}` 初始化。")
            return

        # 準備嵌入消息
        embed = discord.Embed(
            title=f"📅 {date} 的計畫表",
            description="以下是當日的代辦事項：",
            color=discord.Color.blue()
        )
        
        for time_period, task in data[date].items():
            embed.add_field(name=time_period, value=task, inline=False)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"⚠️ 發生錯誤：{str(e)}")

# 指令：查看月曆視圖
from calendar import Calendar


@bot.command(name="view_calendar")
async def view_calendar(ctx, year_month: str):
    """
    查看某月的計畫表，過去的日期劃掉。
    使用格式: !view_calendar YYYY-MM
    """
    try:
        # 確保輸入的格式正確
        if "-" not in year_month or len(year_month.split("-")) != 2:
            raise ValueError("日期格式錯誤")

        year, month = map(int, year_month.split("-"))
        if not (1 <= month <= 12):
            raise ValueError("月份必須在 1 到 12 之間")

        # 生成月曆
        cal = Calendar()
        weeks = cal.monthdayscalendar(year, month)

        # 當前日期
        today = datetime.now().date()
        data = load_data()

        embed = discord.Embed(
            title=f"📅 {year} 年 {month} 月計畫表",
            description="當月計畫（已過去的日期會劃掉）。",
            color=discord.Color.blue(),
        )

        for week_idx, week in enumerate(weeks):
            week_plan = ""
            for day in week:
                if day == 0:  # 空白日
                    continue
                date_str = f"{year}-{month:02d}-{day:02d}"
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                is_past = date_obj < today

                # 任務內容
                if date_str in data:
                    tasks = "\n".join([f"{time}: {task}" for time, task in data[date_str].items()])
                    task_display = tasks if not is_past else f"~~{tasks}~~"
                else:
                    task_display = "無計畫" if not is_past else "~~無計畫~~"

                # 日期顯示
                date_display = f"~~{day} 日~~" if is_past else f"{day} 日"
                week_plan += f"{date_display}:\n{task_display}\n\n"

            if week_plan:
                embed.add_field(name=f"第 {week_idx + 1} 週", value=week_plan, inline=False)

        await ctx.send(embed=embed)

    except ValueError as e:
        await ctx.send(f"❌ 日期格式錯誤：{str(e)}！請使用 YYYY-MM 格式，例如 `!view_calendar 2024-12`。")
    except Exception as e:
        await ctx.send(f"⚠️ 發生未知錯誤：{str(e)}")


# 指令：完成任務
@bot.command(name="complete_task")
async def complete_task(ctx, date: str, time_period: str):
    """
    標記某個時段的任務為完成。
    使用格式: !complete_task YYYY-MM-DD 8-10時
    """
    try:
        data = load_data()

        if date not in data:  # 驗證日期是否存在
            await ctx.send(f"❌ {date} 尚未建立計畫表！請先使用 `!start_plan {date}` 初始化。")
            return

        if time_period not in data[date]:  # 驗證時段是否正確
            await ctx.send(f"❌ 時段 {time_period} 無效！請使用這些時段之一：{', '.join(data[date].keys())}")
            return

        # 標記完成
        data[date][time_period] = f"✅ {data[date][time_period]}"
        save_data(data)
        await ctx.send(f"🎉 已成功標記 {date} 的 {time_period} 任務為完成！")
    except Exception as e:
        await ctx.send(f"⚠️ 發生錯誤：{str(e)}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# 全局錯誤處理
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ 找不到這個指令，請確保您輸入的指令正確。")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ 您缺少必要的參數！請使用 `!help` 查詢指令格式。")
    else:
        await ctx.send(f"⚠️ 發生錯誤：{str(error)}")
        print(f"錯誤: {error}")
        
bot.run("這裡是discord辨識碼")
