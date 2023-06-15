import threading
from bs4 import BeautifulSoup
import requests
import pandas as pd
import time
from tqdm import tqdm

data_lock = threading.Lock()
data = []
failed_ids = []

def getScriptInfo(id):
    url = "https://greasyfork.org/zh-CN/scripts/" + str(id)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    script_info = soup.find("section", attrs={"id": "script-info"})

    if script_info is None:
        if response.text.find("请求的脚本已被删除。") != -1:
            print(f"id:{id} 已被删除。")
        else:
            with data_lock:
                failed_ids.append(id)
    else:
        name = script_info.find("h2").string
        description = script_info.find("p", attrs={"id": "script-description"}).string
        author = script_info.find("dd", attrs={"class": "script-show-author"}).find("span").find("a").string

        # 创建包含数据的 DataFrame
        script_data = {
            "ID": id,
            "名称": name,
            "描述": description,
            "作者": author,
            "URL": url
        }

        with data_lock:
            data.append(script_data)

def getAllScriptInfo(start_id, end_id, num_threads):
    # 读取现有数据
    try:
        existing_data = pd.read_excel("script_info.xlsx")
        existing_ids = set(existing_data["ID"].tolist())
        start_id = max(start_id, max(existing_ids) + 1)
        print(f"已读取的脚本ID: {existing_ids}")
    except FileNotFoundError:
        existing_data = None

    threads = []
    progress_bar = tqdm(total=end_id - start_id + 1, desc="进度")

    for id in range(start_id, end_id + 1):
        if existing_data is not None and id in existing_ids:
            progress_bar.update(1)
            continue

        thread = threading.Thread(target=getScriptInfo, args=(id,))
        threads.append(thread)
        thread.start()

        if len(threads) >= num_threads:
            for thread in threads:
                thread.join()

            threads = []
            progress_bar.update(num_threads)

    for thread in threads:
        thread.join()
        progress_bar.update(1)

    progress_bar.close()

    if data:
        # 将字典对象转换为 DataFrame
        data_frames = [pd.DataFrame([d]) for d in data]

        # 拼接所有的 DataFrame 对象
        combined_df = pd.concat(data_frames, ignore_index=True)


        if existing_data is not None:
            combined_df = pd.concat([existing_data, combined_df], ignore_index=True)

        combined_df.to_excel("script_info.xlsx", index=False)
        print("数据保存至 script_info.xlsx")

    if failed_ids:
        failed_range = f"{failed_ids[0]}-{failed_ids[-1]}"
        failed_info = {
            "未成功爬取的脚本ID范围": [failed_range],
            "未成功爬取的脚本ID": [",".join(map(str, failed_ids))]
        }
        failed_df = pd.DataFrame(failed_info)

        with pd.ExcelWriter("script_info.xlsx", mode="a", engine="openpyxl") as writer:
            failed_df.to_excel(writer, sheet_name="未成功爬取的脚本ID", index=False)

        print("未成功爬取的脚本ID已记录至 script_info.xlsx")




start_id, end_id, num_threads = 1, 250, 5


getAllScriptInfo(start_id, end_id, num_threads)
