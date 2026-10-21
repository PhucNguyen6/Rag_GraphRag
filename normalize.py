
import json
from pathlib import Path

RAW = Path("raw")
DOCS_OUT = Path("documents.jsonl")
ENTITIES_OUT = Path("entities.jsonl")


def get_documents(data):
    """Hỗ trợ các cấu trúc BioC JSON phổ biến."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    if isinstance(data.get("documents"), list):
        return data["documents"]

    if isinstance(data.get("PubTator3"), list):
        return data["PubTator3"]

    return []


def normalize(doc):
    passages = doc.get("passages", [])
    parts = []
    entities = []

    for passage in passages:
        info = passage.get("infons") or {}
        text = (passage.get("text") or "").strip()

        if text:
            section = (
                info.get("section")
                or info.get("type")
                or info.get("section_type")
                or "text"
            )
            parts.append(f"[{section}]\n{text}")

        for ann in passage.get("annotations", []):
            ai = ann.get("infons") or {}
            locations = ann.get("locations") or []

            entities.append({
                "text": ann.get("text", ""),
                "type": ai.get("type") or ann.get("type"),
                "identifier": (
                    ai.get("identifier")
                    or ann.get("identifier")
                    or ann.get("normalizedId")
                ),
                "locations": locations,
            })

    info = doc.get("infons") or {}
    pmid = (
        info.get("article-id_pmid")
        or info.get("pmid")
        or doc.get("pmid")
        or doc.get("id")
        or ""
    )
    title = info.get("title") or ""
    if not title:
        for passage in passages:
            pinfo = passage.get("infons") or {}
            ptype = str(
                pinfo.get("type") or pinfo.get("section_type") or ""
            ).lower()

            if ptype == "title":
                title = (passage.get("text") or "").strip()
                if title:
                    break

    text = "\n\n".join(parts).strip()
    if not text:
        return None

    return {
        "id": str(pmid),
        "title": title,
        "source": "PubTator Central",
        "text": text,
        "entities": entities,
    }


def main():
    files = sorted(RAW.glob("*.json"))
    if not files:
        raise FileNotFoundError("Không có file JSON trong raw/.")

    count_docs = count_entities = 0
    seen = set()

    with DOCS_OUT.open("w", encoding="utf-8") as df, \
         ENTITIES_OUT.open("w", encoding="utf-8") as ef:

        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            documents = get_documents(data)

            print(f"{path}: tìm thấy {len(documents)} tài liệu")

            if not documents:
                print("  Keys gốc:", list(data.keys())
                      if isinstance(data, dict) else type(data).__name__)
                continue

            for doc in documents:
                record = normalize(doc)
                if not record:
                    continue

                key = record["id"] or f"{path.name}:{count_docs}"
                if key in seen:
                    continue
                seen.add(key)

                df.write(json.dumps(record, ensure_ascii=False) + "\n")
                count_docs += 1

                for entity in record["entities"]:
                    ef.write(json.dumps({
                        "document_id": record["id"],
                        **entity,
                    }, ensure_ascii=False) + "\n")
                    count_entities += 1

    print(f"Đã chuẩn hóa: {count_docs} tài liệu")
    print(f"Đã xuất: {count_entities} annotation")
    print("Đầu ra:", DOCS_OUT, ENTITIES_OUT)


if __name__ == "__main__":
    main()
