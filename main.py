from tqdm import tqdm
from bs4 import BeautifulSoup
import threading
import requests
import pandas as pd
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('start_id', type=int)
parser.add_argument('end_id', type=int)
parser.add_argument('num_threads', type=int)
args = parser.parse_args()

start_id = args.start_id
end_id = args.end_id
num_threads = args.num_threads

data_lock = threading.Lock()
data = []
failed_ids = []

def getScriptInfo(id):
    url = "https://greasyfork.org/zh-CN/scripts/" + str(id)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    script_info = soup.find("section", attrs={"id": "script-info"})

    if script_info is None:
        if "已被删除。" in response.text or "This script has been deleted" in response.text:
            print(f"id:{id} 已被删除。")
        elif response.text.find("404") != -1:
            print(f"id:{id} 访问404")
        else:
            with data_lock:
                failed_ids.append(id)
    else:
        name = None
        description = None
        author = None
        site = None
        license = None

        try:
            name = script_info.find("h2").string
            description = script_info.find("p", attrs={"id": "script-description"}).string
            author = script_info.find("dd", attrs={"class": "script-show-author"}).find("span").find("a").string
            site = script_info.find("ul", attrs={"class": "block-list"}).find("li").find("a").string
            license = script_info.find("dd", attrs={"class": "script-show-license"}).find("span").string
        except AttributeError:
            pass

        # 创建包含数据的字典
        script_data = {
            "id": id,
            "名称": name,
            "描述": description,
            "作者": author,
            "URL": url,
            "应用到": site,
            "许可证": license
        }

        with data_lock:
            data.append(script_data)

def getAllScriptInfo(start_id, end_id, num_threads):
    # 读取现有数据
    try:
        existing_data = pd.read_csv("script_info.csv")
        existing_ids = set(existing_data["id"].tolist())
        start_id = max(start_id, max(existing_ids) + 1)
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
        combined_df = pd.DataFrame(data)

        if existing_data is not None:
            combined_df = pd.concat([existing_data, combined_df], ignore_index=True)

        combined_df.to_csv("script_info.csv", index=False)
        print("数据保存至 script_info.csv")

    if failed_ids:
        print("以下id请求失败：",failed_ids)
    # 读取CSV文件
    data_frame = pd.read_csv("script_info.csv")

    # 按ID列进行升序排序
    sorted_data = data_frame.sort_values("id")

    # 将排序后的数据覆盖原始CSV文件
    sorted_data.to_csv("script_info.csv", index=False)

    print("数据已按ID排序并保存至 script_info.csv 文件。")


getAllScriptInfo(start_id, end_id, num_threads)