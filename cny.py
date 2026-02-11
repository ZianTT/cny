import time
import requests

CSRF = ""
SESSDATA = ""
DELAY = 100
CHECK_ROOM_DELAY = 5000
HUNT_THRESHOLD = 5000

session = bilibili_util.BilibiliClient()
session.session.headers.update(
    {"buvid": session.buvid}
)


def fetch_chat_rooms():
    url = 'https://api.live.bilibili.com/live.center.interface.v1.Chat/GetChatRoomsDetail'

    page = 1
    fetched_ids = []
    ret_text = ""
    while True:
        params = {
            "page": page,
            "room_id": "26271604",
            "exist_ids": ','.join(fetched_ids)
        }
        response = session.get(url, params=params)
        data = response
        # print(data)
        for room in data.get('data', {}).get('chat_rooms', []):
            fetched_ids.append(str(room['room_id']))
            fortune = 0
            if "万" in room['fortune_value_str']:
                fortune = int(float(room['fortune_value_str'].replace("万", "")) * 10000)
            else:
                fortune = int(room['fortune_value_str'])
            delta = 999999999999
            target = 0
            if fortune < 250000:
                delta = 250000 - fortune
                target = 250000
            elif fortune > 250000 and fortune < 1000000:
                delta = 1000000 - fortune
                target = 1000000
            else:
                pass
            if delta < 100000:
                ret_text += f"https://live.bilibili.com/{room['room_id']} {room['title']} 距 {target} 节点 差约 {delta//1000}K\n\n"
        page += 1
        if not data.get('data', {}).get('has_more', False):
            break
    ret_text += f"\n共抓取了 {len(fetched_ids)} 个房间"
    return ret_text

def fetch_recommend_roomid():
    url = 'https://api.live.bilibili.com/live.center.interface.v1.Chat/GetChatRoomsDetail'

    page = 1
    fetched_ids = []
    preferred_room_id = None
    preferred_delta = 999999999999

    while True:
        params = {
            "page": page,
            "room_id": "26271604",
            "exist_ids": ','.join(fetched_ids)
        }
        try:
            response = session.get(url, params=params)
            data = response
        except Exception as e:
            print("Error fetching chat rooms:", e)
            continue
        for room in data.get('data', {}).get('chat_rooms', []):
            fetched_ids.append(str(room['room_id']))
            fortune = 0
            if "万" in room['fortune_value_str']:
                fortune = int(float(room['fortune_value_str'].replace("万", "")) * 10000)
            else:
                fortune = int(room['fortune_value_str'])
            delta = 999999999999
            target = 0
            if fortune < 250000:
                delta = 250000 - fortune
                target = 250000
            elif fortune > 250000 and fortune < 1000000:
                delta = 1000000 - fortune
                target = 1000000
            else:
                pass
            if delta < HUNT_THRESHOLD:
                if delta < preferred_delta:
                    preferred_room_id = room['room_id']
                    preferred_delta = delta
        page += 1
        if not data.get('data', {}).get('has_more', False):
            break
    return preferred_room_id

def fetch_room_next_task_info(room_id):
    url = 'https://api.bilibili.com/x/custom_activity/cny/2026/live/task'
    params = {
        "room_id": room_id
    }
    response = session.get(url, params=params)
    data = response
    # fortune_value
    now = data.get('data', {}).get('fortune_value', 0)
    for step in data.get('data', {}).get('steps', []):
        if step['limit'] > now and step['bonus']['no'] in [1, 2]:
            param = {
                "room_id": room_id,
                "no": step['bonus']['no'],
                "id": step['bonus']['id'],
                "sub_task_id": step['bonus']['sub_task_id']
            }
            return param
    return None

def receive_bonus(param):
    global CSRF, SESSDATA
    url = f'https://api.bilibili.com/x/custom_activity/cny/2026/bonus/receive'
    response = session.post(url, params={"csrf": CSRF},json=param, headers={"Cookie": f"SESSDATA={SESSDATA}"})
    return response

if __name__ == "__main__":
    # print(fetch_chat_rooms())
    while True:
        print("Fetching recommended room ID...")
        try:
            room_id = fetch_recommend_roomid()
        except Exception as e:
            print(f"Error fetching recommended room ID: {e}")
            continue
        room_id = 42062
        if room_id is None:
            print("No suitable room found.")
            time.sleep(CHECK_ROOM_DELAY/1000)
        else:
            print(f"Recommended room ID: {room_id}")
            print("Fetching task info...")
            try:
                params = fetch_room_next_task_info(room_id)
            except Exception as e:
                print(f"Error fetching task info: {e}")
                params = None
            print(params)
            if params:
                session.wbi = True
                while True:
                    try:
                        result = receive_bonus(params)
                    except Exception as e:
                        print(f"Error receiving bonus: {e}")
                        continue
                    print(result)
                    if result.get('code') == 0:
                        print("Bonus received successfully!")
                        break
                    elif result.get("message") == "抢光":
                        print("Bonus empty.")
                        break
                    elif result.get("data", {}).get("reason", "") == "gray":
                        print("May risked, stop trying.")
                        break
                    time.sleep(DELAY/1000)
                session.wbi = False
