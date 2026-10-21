
import json
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RAW = Path("raw")
RAW.mkdir(exist_ok=True)

N = 300 # 300 papers, major in COVID-19 and SARS-CoV-2

QUERY = "(COVID-19[Majr] OR SARS-CoV-2[Majr])"

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EXPORT = (
    "https://www.ncbi.nlm.nih.gov/research/"
    "pubtator-api/publications/export/biocjson"
)

session = requests.Session()
retry = Retry(
    total=4,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods={"GET"},
)
session.mount("https://", HTTPAdapter(max_retries=retry))

last_request = 0.0
MIN_INTERVAL = 0.5


def get(url, params):
    global last_request

    wait = MIN_INTERVAL - (time.monotonic() - last_request)
    if wait > 0:
        time.sleep(wait)

    last_request = time.monotonic()
    response = session.get(url, params=params, timeout=120)
    response.raise_for_status()
    return response


def main():
    query_file = RAW / "query.txt"
    refresh_cache = (
        not query_file.exists()
        or query_file.read_text(encoding="utf-8") != QUERY
    )

    response = get(ESEARCH, {
        "db": "pubmed",
        "term": QUERY,
        "retmax": N,
        "sort": "relevance",
        "retmode": "json",
    })

    pmids = response.json()["esearchresult"]["idlist"]
    if not pmids:
        raise RuntimeError("Không tìm thấy PMID.")

    (RAW / "pmids.txt").write_text(
        "\n".join(pmids) + "\n", encoding="utf-8"
    )
    print(f"Đã lấy {len(pmids)} PMID.")

    if refresh_cache:
        print("Truy vấn thay đổi hoặc chưa có metadata; sẽ tải lại các batch.")

    for start in range(0, len(pmids), 100):
        batch = pmids[start:start + 100]
        output = RAW / f"bioc_{start // 100:03d}.json"

        if not refresh_cache and output.exists() and output.stat().st_size > 0:
            print("Đã tồn tại:", output)
            continue

        response = get(EXPORT, {"pmids": ",".join(batch)})
        data = response.json()

        temp = output.with_suffix(".tmp")
        temp.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )
        temp.replace(output)

        print("Đã lưu:", output)

    query_file.write_text(QUERY, encoding="utf-8")
    print("Hoàn tất tải dữ liệu vào raw/.")


if __name__ == "__main__":
    main()
