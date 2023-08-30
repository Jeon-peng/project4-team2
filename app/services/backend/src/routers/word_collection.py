from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from datetime import datetime, timedelta
from ..database import fetch_query

current_time = datetime.now()
start_example = (current_time - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
end_example = current_time.strftime('%Y-%m-%d %H:%M:%S')


router = APIRouter()

@router.get("/rank",
    summary="틀린 단어와 수정된 단어 개수 가져오기",
    description="""
## Summary :
각 태그 별, 전체 태그로 해서 각 날짜 ( 1시간 단위 ) 별 ( 틀리게 작성된 됫글 / 수정된 적절한댓글 / 해당시간대에 언급된 횟수) 를 나타낸다

## Parameters:

- `start_time`: 시작 시간을 지정합니다. 
    - 포맷: 'YYYY-MM-DD HH:MM:SS'
    - 예: '2023-01-01 12:00:00'
  
- `end_time`: 끝 시간을 지정합니다. 
    - 포맷: 'YYYY-MM-DD HH:MM:SS'
    - 예: '2023-01-02 12:00:00'
    
- `tag`: 특정 태그와 관련된 댓글을 필터링 하기 위해 사용됩니다.

## Note:

시작 시간과 끝 시간을 모두 지정하지 않으면, 기본적으로 최근 24시간 동안의 댓글을 반환합니다.  
태그를 지정하지 않으며면, 전체 태그를 반환합니다.  

## Request Example:
- GET /word_collection/rank?start_Time=2023-08-27 22:12:03&end_time=2023-08-28 22:12:03
- GET /word_collection/rank?tag=news
- GET /word_collection/rank

**Response:**

- **200 OK**  
요청이 성공적으로 처리되었으며, 해당 조건에 맞는 댓글 목록을 반환합니다.  
응답 본문 예시:
```json
[
  {
    "timestamp": "2023-08-28 04:00:00",
    "total": [
      {
        "incorrect_word": "궃이",
        "correct_word": "굳이",
        "occurrence_count": 31,
        "rank": 1
      },
      {
        "incorrect_word": "역활",
        "correct_word": "역할",
        "occurrence_count": 28,
        "rank": 2
      },
      {
        "incorrect_word": "일부로",
        "correct_word": "일부러",
        "occurrence_count": 26,
        "rank": 3
      },
      {
        "incorrect_word": "곰곰히",
        "correct_word": "곰곰이",
        "occurrence_count": 24,
        "rank": 4
      },
      {
        "incorrect_word": "일찍기",
        "correct_word": "일찍이",
        "occurrence_count": 23,
        "rank": 5
      },
      {
        "incorrect_word": "깨끗히",
        "correct_word": "깨끗이",
        "occurrence_count": 22,
        "rank": 6
      },
      {
        "incorrect_word": "가벼히",
        "correct_word": "가벼이",
        "occurrence_count": 21,
        "rank": 7
      },
      {
        "incorrect_word": "일부로",
        "correct_word": "일부러",
        "occurrence_count": 20,
        "rank": 8
      },
      {
        "incorrect_word": "궃이",
        "correct_word": "굳이",
        "occurrence_count": 20,
        "rank": 9
      },
      {
        "incorrect_word": "금새",
        "correct_word": "금세",
        "occurrence_count": 19,
        "rank": 10
      }
    ]
  },,...
```
- **204 No Content**  
해당 기간 또는 태그에 맞는 댓글이 존재하지 않을 경우 반환됩니다. 본문 내용이 없음을 나타냅니다.

- **500 Internal Server Error**  
서버 내부 오류 또는 데이터베이스 연결 실패 시 반환됩니다.
응답 본문 예시:
```json
{
    "detail": "Unable to connect to the database."
}
```

    """
)
def get_rank(
    start_time: str = Query(default=start_example, example=start_example, description="시작 시간"),
    end_time: str = Query(default=end_example, example=end_example, description="끝 시간"),
    tag: str = Query(None, description="태그 [ youtube, news, webtoon ]")
) -> List[Dict[str, Any]]:
    try:
        if start_time:
            start_date_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        else:
            start_date_dt = datetime.now() - timedelta(hours=24)

        if end_time:
            end_date_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        else:
            end_date_dt = datetime.now()

        raw_data = fetch_query.fetch_word_corrections_from_db(start_date_dt, end_date_dt)

        if not raw_data:
            raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)

        processed_data = {}
        for record in raw_data:
            timestamp, incorrect_word, correct_word, content_tag, occurrence_count, rank = record
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

            if timestamp_str not in processed_data:
                processed_data[timestamp_str] = {}

            if content_tag not in processed_data[timestamp_str]:
                processed_data[timestamp_str][content_tag] = []

            processed_data[timestamp_str][content_tag].append({
                "incorrect_word": incorrect_word,
                "correct_word": correct_word,
                "occurrence_count": occurrence_count,
                "rank": rank
            })

        result = []

        for timestamp, content_data in sorted(processed_data.items()):
            timestamp_data = {"timestamp": timestamp}

            if tag:
                if tag in content_data:
                    sorted_words = sorted(content_data[tag], key=lambda x: x["occurrence_count"], reverse=True)
                    unique_ranks = set()
                    result_words = []

                    for word in sorted_words:
                        if word["rank"] not in unique_ranks:
                            result_words.append(word)
                            unique_ranks.add(word["rank"])
                        if len(result_words) >= 10:
                            break

                    timestamp_data[tag] = result_words
                else:
                    continue
            else:
                all_words = []
                for words in content_data.values():
                    all_words.extend(words)
                all_words.sort(key=lambda x: x["occurrence_count"], reverse=True)

                unique_ranks = set()
                result_words = []

                for word in all_words:
                    if word["rank"] not in unique_ranks:
                        result_words.append(word)
                        unique_ranks.add(word["rank"])
                    if len(result_words) >= 10:
                        break

                timestamp_data["total"] = result_words

            result.append(timestamp_data)

        return result

    except ConnectionError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to connect to the database.")
      
      
@router.get(
  "/word_tags",
  summary="특정 단어 현황 보여주기",
    description="""
## Summary :
특정 단어를 검색하여 해당 단어의 상태 ( 틀린단어 or 수정된 단어 ) 를 파악하여 시간대 별 현황을 보여줍니다.
    
## Parameters:

- `start_time`: 시작 시간을 지정합니다. 
    - 포맷: 'YYYY-MM-DD HH:MM:SS'
    - 예: '2023-01-01 12:00:00'
  
- `end_time`: 끝 시간을 지정합니다. 
    - 포맷: 'YYYY-MM-DD HH:MM:SS'
    - 예: '2023-01-02 12:00:00'
    
- `search_word: 검색할 단어 ( 틀린단어 or 수정될 단어 )

## Note:

시작 시간과 끝 시간을 모두 지정하지 않으면, 기본적으로 최근 24시간 동안의 댓글을 반환합니다.  
태그를 지정하지 않으며면, 전체 태그를 반환합니다.  

## Request Example:
- GET /word_collection/word_tags/?start_Time=2023-08-27 22:12:03&end_time=2023-08-28 22:12:03
- GET /word_collection/word_tags/?search_word=궃이
- GET /word_collection/word_tags

**Response:**    
    
    
- **200 OK**  
요청이 성공적으로 처리되었으며, 해당 조건에 맞는 댓글 목록을 반환합니다.  
응답 본문 예시:
```json
    [
  {
    "timestamp": "2023-08-28 16:00:00",
    "total": 1058,
    "news": 335,
    "webtoon": 363,
    "youtube": 360,
    "search_word": "궃이",
    "incorrect_word": [
      "궃이"
    ],
    "correct_word": [
      "굳이"
    ]
  },
  {
    "timestamp": "2023-08-28 17:00:00",
    "total": 954,
    "news": 325,
    "webtoon": 316,
    "youtube": 313,
    "search_word": "궃이",
    "incorrect_word": [
      "궃이"
    ],
    "correct_word": [
      "굳이"
    ]
  },,...
```

- **204 No Content**  
해당 기간 또는 태그에 맞는 댓글이 존재하지 않을 경우 반환됩니다. 본문 내용이 없음을 나타냅니다.

- **500 Internal Server Error**  
서버 내부 오류 또는 데이터베이스 연결 실패 시 반환됩니다.
응답 본문 예시:
```json
{
    "detail": "Unable to connect to the database."
}
```

    """
)
def get_word_tags(
    start_time: str = Query(default=start_example, example=start_example, description="시작 시간"),
    end_time: str = Query(default=end_example, example=end_example, description="끝 시간"),
    search_word: str = Query(default='궃이', example='궃이', description="검색할 단어 ( 틀린단어, 수정될단어 다 가능 )")
) -> List[Dict[str, Any]]:
  try :
    if start_time:
        start_date_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    else:
        start_date_dt = datetime.now() - timedelta(hours=24)

    if end_time:
        end_date_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    else:
        end_date_dt = datetime.now()

    # 날짜 별 태그 별 언급 횟수를 저장할 딕셔너리
    mention_counts = {}

    # 데이터베이스에서 데이터 가져오기
    raw_data = fetch_query.fetch_word_corrections_from_db(start_date_dt, end_date_dt)

    
    if raw_data is None:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)

    for record in raw_data:
        timestamp, incorrect_word, correct_word, content_tag, occurrence_count, rank = record
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        if timestamp_str not in mention_counts:
            mention_counts[timestamp_str] = {
                "total": 0,
                "news": 0,
                "webtoon": 0,
                "youtube": 0,
                "search_word": search_word,
                "incorrect_word": [],
                "correct_word": []
            }

        mention_counts[timestamp_str][content_tag] += occurrence_count
        mention_counts[timestamp_str]["total"] += occurrence_count

        if (search_word == incorrect_word) or (search_word == correct_word):
            if (incorrect_word not in mention_counts[timestamp_str]["incorrect_word"]):
                mention_counts[timestamp_str]["incorrect_word"].append(incorrect_word)
            if  (correct_word not in mention_counts[timestamp_str]["correct_word"]):
                mention_counts[timestamp_str]["correct_word"].append(correct_word)


    # 결과 데이터 생성
    result = []
    for timestamp, tag_counts in mention_counts.items():
        result.append({
            "timestamp": timestamp,
            **tag_counts
        })

    return result
  
  except ConnectionError:  # 데이터베이스 연결에 실패한 경우에 대한 예외
        raise HTTPException(status_code=500, detail="Unable to connect to the database.")