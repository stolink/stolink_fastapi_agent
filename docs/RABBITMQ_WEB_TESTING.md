# RabbitMQ Web Publishing & Webhook Testing Guide

This guide details how to test the StoLink AI Backend using **Docker**, **RabbitMQ Web UI**, and an external **Webhook** service.

## 1. Start Environment with Docker

Use Docker Compose to start the entire stack (PostgreSQL, Neo4j, RabbitMQ, AI Backend).

```bash
docker-compose up -d --build
```
*Wait for all services to become healthy.*

## 2. Prepare Webhook

1.  Go to a webhook testing site like [Webhook.site](https://webhook.site).
2.  Copy your unique URL (e.g., `https://webhook.site/uuid-aaaa-bbbb...`).
3.  Keep this window open to receive the callback.

## 3. Access RabbitMQ Web UI

1.  Open your browser and navigate to: [http://localhost:15672](http://localhost:15672)
2.  Login with default credentials:
    -   Username: `guest`
    -   Password: `guest`

## 4. Publish Message

1.  Navigate to the **Queues** tab.
2.  Find and click on `stolink.analysis.queue`.
3.  Expand the **Publish message** section.
4.  Copy the JSON Payload below, **replace `YOUR_WEBHOOK_URL_HERE` with your Webhook URL**, and paste it into the **Payload** box.
5.  Click **Publish message**.

### Payload Template

```json
{
  "job_id": "test-story-complex-02",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_id": "doc-temple-complex",
  "content": "육중한 문이 열리자마자 리안은 본능적으로 몸을 굴려 기둥 뒤로 숨었다. 아니나 다를까, 그가 서 있던 자리에 푸른색 섬광이 스치고 지나가며 돌바닥을 검게 그을렸다. \"여전히 쥐새끼처럼 빠르네, 리안.\" 어둠 속에서 비꼬는 듯한 차가운 목소리가 들려왔다. 기둥 너머에서 베라(Vera)가 천천히 걸어 나왔다. 그녀는 붉은 벨벳 코트를 우아하게 걸치고 있었지만, 오른쪽 눈에는 검은 안대를 하고 있어 위압적인 분위기를 풍겼다. 그녀의 손에는 아직 연기가 피어오르는 '폭풍의 지팡이'가 들려 있었다. 리안은 이를 악물며 단검을 고쳐 잡았다. \"베라... 네가 여기서 뭘 하고 있지? 이건 '검은 까마귀' 용병단이 낄 일이 아니야.\" \"오해하지 마. 난 단지 의뢰를 받았을 뿐이니까.\" 베라는 지팡이 끝으로 리안을 겨누며 피식 웃었다. 그녀의 표정에는 여유와 경멸이 뒤섞여 있었다. 하지만 그녀의 뒤에는 또 다른 인물이 서 있었다. 티오(Tio)였다. 그는 베라와 달리 잔뜩 겁에 질린 표정으로 거대한 짐 가방을 힘겹게 짊어지고 있었다. 앳된 얼굴의 소년은 떨리는 목소리로 베라의 옷자락을 잡았다. \"대, 대장님. 약속이랑 다르잖아요. 그냥 조사만 한다고 하셨으면서... 리안 형을 죽일 셈이에요?\" 티오의 말에 리안의 눈빛이 흔들렸다. \"티오? 네가 왜 그 여자랑 있어! 3년 전, 너와 내 동생을 구해주기로 한 약속을 잊은 거야?\" 티오는 리안의 시선을 피하며 고개를 숙였다. 그의 손에는 '망가진 회중시계'가 꽉 쥐어져 있었다. 그것은 과거 리안이 그에게 선물했던 우정의 증표였다. 티오가 울먹이며 소리쳤다. \"형은 우릴 버렸잖아요! 그때 마을이 불탈 때... 형은 도망쳤어!\" \"난 도망친 게 아니야! 지원군을 부르러 갔던 거라고!\" 리안이 억울함과 분노에 차서 소리쳤지만, 베라가 그 말을 끊었다. \"지루한 추억팔이는 거기까지.\" 베라의 눈빛이 살기로 번뜩였다. \"티오, 놈을 묶어. 이 사원의 보물인 '영원의 성배'를 얻으려면 살아있는 제물이 필요하니까.\" 베라는 품에서 황금빛 두루마리를 꺼내 주문을 외우기 시작했고, 리안은 티오의 망설임을 틈타 베라의 옆구리를 노리고 전력질주했다. 폭풍우 소리보다 더 큰 고함이 사원 내부를 울렸다.",
  "context": {
    "chapter_number": 2,
    "total_chapters": 10,
    "existing_characters": [
      {
        "id": "char-rian-001",
        "name": "리안",
        "role": "protagonist"
      }
    ],
    "existing_events": [],
    "existing_relationships": [],
    "existing_settings": [],
    "world_rules_summary": "고대 사원에는 강력한 힘을 가진 유물이 숨겨져 있으며, '검은 까마귀' 용병단이 개입해 있다."
  },
  "callback_url": "https://webhook.site/be6e2bb0-dc6a-498a-886c-267978d0abed",
  "trace_id": "trace-complex-test-02"
}
```

## 5. Verify Results

1.  **RabbitMQ UI**: The message count in the queue should briefly go up and then down (consumed by backend).
2.  **Docker Logs**: View backend logs to see processing:
    ```bash
    docker logs -f stolink-ai-backend
    ```
    You should see "Received analysis task" and eventually "Analysis task completed".
3.  **Webhook Site**: Check your Webhook window. You should receive a `POST` request with the analysis result JSON.

## Troubleshooting

-   **Message stuck in queue**: Check if `ai-backend` container is running (`docker ps`).
-   **No callback received**: Check Docker logs for errors. Ensure the `callback_url` is accessible from the Docker container (public URLs like webhook.site work fine).
