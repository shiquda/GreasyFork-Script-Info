from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm
import threading
import requests
import argparse
import csv
import time

parser = argparse.ArgumentParser()
parser.add_argument('start_id', type=int)
parser.add_argument('end_id', type=int)
parser.add_argument('num_threads', type=int)
args = parser.parse_args()

start_id = args.start_id
end_id = args.end_id
num_threads = args.num_threads

lock = threading.Lock()
data = []
failed_ids = []

def getScriptInfo(id):
    url = "https://greasyfork.org/zh-CN/scripts/" + str(id)
    try:
        response = session.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        script_info = soup.find("section", attrs={"id": "script-info"})

        if script_info is None:
            if "已被删除。" in response.text or "This script has been deleted" in response.text:
                print(f"id:{id} 已被删除。")
            elif response.text.find("404") != -1:
                print(f"id:{id} 访问404")
            else:
                with lock:
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

            script_data = {
                "id": id,
                "名称": name,
                "描述": description,
                "作者": author,
                "URL": url,
                "应用到": site,
                "许可证": license
            }

            with lock:
                data.append(script_data)
    except Exception as e:
        print(f"请求id:{id}时出错：{str(e)}")

def processBatch(start_id, end_id, batch_size):
    futures = []
    progress_bar = tqdm.tqdm(total=end_id - start_id + 1, desc="进度")

    for id in range(start_id, end_id + 1, batch_size):
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            batch = range(id, min(id + batch_size, end_id + 1))
            for id in batch:
                future = executor.submit(getScriptInfo, id)
                futures.append(future)

            for future in as_completed(futures):
                future.result()
                progress_bar.update(1)

    progress_bar.close()

    if data:
        with lock:
            existing_data = []
            try:
                with open("script_info.csv", "r") as f:
                    reader = csv.DictReader(f)
                    existing_data = list(reader)
            except FileNotFoundError:
                existing_data = []

            combined_data = existing_data + data

            with open("script_info.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=combined_data[0].keys())
                writer.writeheader()
                writer.writerows(combined_data)

        print("数据保存至 script_info.csv")

    if failed_ids:
        print("以下id请求失败：", failed_ids)

    print("数据已按ID排序并保存至 script_info.csv 文件。")

# 使用连接池来管理与远程服务器的连接
session = requests.Session()

start_time = time.time()
processBatch(start_id, end_id, 100)
end_time = time.time()
execution_time = end_time - start_time

print(f"脚本已优化完成，总耗时: {execution_time}秒")
