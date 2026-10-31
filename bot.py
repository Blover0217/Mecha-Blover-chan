
import os
import discord
import aiohttp

from dotenv import load_dotenv
from discord.ext import tasks

load_dotenv()

# 인증 정보
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHZZK_CLIENT_ID = os.getenv("CHZZK_CLIENT_ID")
CHZZK_CLIENT_SECRET = os.getenv("CHZZK_CLIENT_SECRET")

# 채널 정보
CHZZK_CHANNEL_ID = os.getenv("CHZZK_CHANNEL_ID")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# 치지직 API
CHZZK_API_URL = "https://openapi.chzzk.naver.com/open/v1/lives"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# 이전 방송 상태
previous_live = None


async def check_chzzk_live():
    """치지직 전체 방송 목록에서 지정한 채널 찾기"""

    headers = {
        "Client-Id": CHZZK_CLIENT_ID,
        "Client-Secret": CHZZK_CLIENT_SECRET,
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        next_cursor = None

        while True:
            params = {"size": 20}

            if next_cursor:
                params["next"] = next_cursor

            async with session.get(
                CHZZK_API_URL,
                headers=headers,
                params=params
            ) as response:

                response.raise_for_status()
                result = await response.json()

            content = result.get("content", {})
            lives = content.get("data", [])

            for live in lives:
                if live.get("channelId") == CHZZK_CHANNEL_ID:
                    return live

            page = content.get("page", {})
            next_cursor = page.get("next")

            if not next_cursor:
                return None


@tasks.loop(seconds=60)
async def monitor_live():
    global previous_live

    try:
        live = await check_chzzk_live()
        is_live = live is not None

        # 최초 실행 시 현재 방송 상태만 기록
        if previous_live is None:
            previous_live = is_live

            if is_live:
                print("현재 방송 중입니다. 다음 방송 시작부터 알림을 보냅니다.")
            else:
                print("방송 대기 중입니다.")

            return

        # 방송 시작 감지
        if is_live and not previous_live:
            channel = client.get_channel(DISCORD_CHANNEL_ID)

            if channel is None:
                channel = await client.fetch_channel(DISCORD_CHANNEL_ID)

            title = live.get("liveTitle", "제목 없음")
            url = f"https://chzzk.naver.com/live/{live['liveId']}"

            await channel.send(
                f"🔴 @here **방송이 시작되었습니다!**\n"
                f"📺 {title}\n"
                f"🔗 {url}"
            )

            print("방송 시작 알림 전송 완료!")

        elif not is_live and previous_live:
            print("방송이 종료되었습니다.")

        previous_live = is_live

    except Exception as e:
        print(f"방송 확인 중 오류 발생: {e}")


@monitor_live.before_loop
async def before_monitor():
    await client.wait_until_ready()


@client.event
async def on_ready():
    print(f"봇 접속 성공: {client.user}")

    if not monitor_live.is_running():
        monitor_live.start()


if not all([
    DISCORD_TOKEN,
    CHZZK_CLIENT_ID,
    CHZZK_CLIENT_SECRET,
    CHZZK_CHANNEL_ID,
    DISCORD_CHANNEL_ID
]):
    raise ValueError(".env 파일의 설정을 확인해 주세요.")

client.run(DISCORD_TOKEN)
