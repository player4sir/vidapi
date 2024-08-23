import requests
import time
import json

# API的基础URL
BASE_URL = "http://localhost:8000"


def test_scrape_api():
    print("Testing /scrape endpoint...")

    # 准备请求数据
    scrape_data = {
        "base_url": "https://www.hsck.la",
        "categories": [1, 2],  # 只测试两个分类以加快测试速度
        "max_pages_per_category": 1  # 每个分类只爬取一页
    }

    # 发送POST请求到/scrape端点
    response = requests.post(f"{BASE_URL}/scrape", json=scrape_data)

    # 检查响应状态码
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    # 检查响应内容
    data = response.json()
    assert "task_id" in data, "Response should contain a task_id"
    assert "message" in data, "Response should contain a message"

    print("Scrape request successful. Task ID:", data["task_id"])
    return data["task_id"]


def test_result_api(task_id):
    print(f"Testing /result/{task_id} endpoint...")

    max_attempts = 10
    delay = 5  # 秒

    for attempt in range(max_attempts):
        # 发送GET请求到/result/{task_id}端点
        response = requests.get(f"{BASE_URL}/result/{task_id}")

        # 检查响应状态码
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

        data = response.json()

        if "message" in data and data["message"] == "Task result not found or not ready yet":
            print(
                f"Result not ready yet. Attempt {attempt + 1}/{max_attempts}. Waiting {delay} seconds...")
            time.sleep(delay)
        else:
            print("Result retrieved successfully.")
            # 验证结果结构
            assert isinstance(data, dict), "Result should be a dictionary"
            assert all(isinstance(category, list) for category in data.values(
            )), "Each category should contain a list of items"

            # 打印一些基本信息
            for category, items in data.items():
                print(f"Category {category}: {len(items)} items")
                if items:
                    print(f"First item in category {category}:")
                    print(json.dumps(items[0], indent=2, ensure_ascii=False))
            return

    assert False, f"Failed to retrieve results after {max_attempts} attempts"


if __name__ == "__main__":
    try:
        task_id = test_scrape_api()
        test_result_api(task_id)
        print("All tests passed successfully!")
    except AssertionError as e:
        print(f"Test failed: {str(e)}")
    except Exception as e:
        print(f"An error occurred during testing: {str(e)}")
