# RabbitMQ Web Publishing & Webhook Testing Guide

This guide details how to test the StoLink AI Backend using **Docker**, **RabbitMQ Web UI**, and an external **Webhook** service.

## 1. Start Environment with Docker

Use Docker Compose to start the entire stack (PostgreSQL, Neo4j, RabbitMQ, AI Backend).

```bash
docker-compose up -d --build
```

_Wait for all services to become healthy._

## 2. Prepare Webhook

1.  Go to a webhook testing site like [Webhook.site](https://webhook.site).
2.  Copy your unique URL (e.g., `https://webhook.site/uuid-aaaa-bbbb...`).
3.  Keep this window open to receive the callback.

## 3. Access RabbitMQ Web UI

1.  Open your browser and navigate to: [http://localhost:15672](http://localhost:15672)
2.  Login with default credentials:
    - Username: `guest`
    - Password: `guest`

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
  "content": "수백 년은 닫혀 있었을 육중한 석문이 기괴한 마찰음을 내며 열렸다. 그 틈새로 쏟아지는 먼지 냄새를 맡자마자, 리안의 등줄기에 서늘한 소름이 돋았다. 뇌가 상황을 판단하기도 전에 몸이 먼저 반응했다. 그는 본능적으로 바닥을 박차고 오른쪽 기둥 뒤로 몸을 날렸다.\n\n콰아앙!\n\n아니나 다를까, 그가 불과 0.1초 전까지 서 있던 자리에 푸른색 섬광이 작렬했다. 단순한 마법 화살이 아니었다. 벼락이 내리꽂힌 듯 돌바닥이 검게 그을리며 매캐한 연기가 피어올랐다. 튀어 오른 돌 파편이 리안의 뺨을 스치고 지나갔다.\n\n\"여전히 쥐새끼처럼 빠르네, 리안. 그 비루한 생존 본능 하나는 인정해 줘야겠어.\"\n\n어둠 속에서 비꼬는 듯한 차가운 목소리가 동굴처럼 울려 퍼졌다. 또각, 또각. 돌바닥을 울리는 구두 굽 소리와 함께 기둥 너머에서 베라(Vera)가 천천히 모습을 드러냈다. 지하 유적의 칙칙한 회색빛과 대비되는 붉은 벨벳 코트가 핏빛처럼 선명했다. 그녀의 오른쪽 눈을 가린 검은 안대는 아름다운 얼굴에 기이한 위압감을 더하고 있었고, 손에 들린 '폭풍의 지팡이' 끝에서는 아직 식지 않은 마력의 잔재가 푸른 연기처럼 피어오르고 있었다.\n\n리안은 혀를 차며 품 안의 단검을 고쳐 잡았다. 손바닥에 땀이 배어 나왔다.\n\n\"베라... 네가 왜 이곳에 있지? 이건 '검은 까마귀' 용병단 따위가 낄 스케일의 일이 아니야.\"\n\n\"오해하지 마. 난 그저 의뢰에 충실할 뿐이니까.\"\n\n베라는 지팡이 끝으로 리안이 숨은 기둥 쪽을 느긋하게 겨누며 피식 웃었다. 그녀의 표정에는 먹잇감을 구석에 몬 포식자의 여유와 경멸이 뒤섞여 있었다. 하지만 리안의 시선은 베라에게 머물지 않았다. 그녀의 등 뒤, 어둠 속에서 쭈뼛거리는 또 다른 인물의 실루엣 때문이었다.\n\n\"설마...\"\n\n그림자 밖으로 나온 것은 티오(Tio)였다. 그는 자기 몸집만 한 거대한 가방을 힘겹게 짊어진 채, 겁에 질린 표정으로 베라의 눈치를 살피고 있었다. 앳된 얼굴의 소년은 리안과 눈이 마주치자 화들짝 놀라며 떨리는 손으로 베라의 붉은 코트 자락을 움켜쥐었다.\n\n\"대, 대장님. 약속이랑 다르잖아요. 분명 조사만 하고 끝낸다고 하셨으면서... 리안 형을 정말 죽일 셈이에요?\"\n\n티오의 입에서 나온 '죽인다'는 단어에 리안의 눈동자가 거칠게 흔들렸다. 배신감보다는 당혹감이 앞섰다.\n\n\"티오? 네가 왜 하필 저 여자랑 있는 거야! 3년 전, 너와 내 동생을 구해주기로 한 약속을 잊은 거야? 우린 가족이나 다름없었잖아!\"\n\n리안의 외침에 티오는 차마 고개를 들지 못했다. 대신 그의 손에 들린 낡은 물건이 리안의 눈에 박혔다. '망가진 회중시계'. 태엽이 멈춘 그 시계는 과거 리안이 고아였던 티오에게 건네주었던 유일한 우정의 증표였다. 티오가 그 시계를 부서질 듯 꽉 쥐며 울먹이는 목소리로 소리쳤다.\n\n\"형은... 형은 우릴 버렸잖아요! 그때 마을이 화염에 휩싸였을 때, 형은 혼자 살겠다고 도망쳤어! 내 눈으로 똑똑히 봤단 말이야!\"\n\n\"난 도망친 게 아니야! 지원군을 부르러 갔던 거라고! 돌아왔을 땐 이미...\"\n\n리안이 억울함과 분노에 차 악을 썼지만, 그의 절규는 베라의 차가운 목소리에 의해 댕강 잘려 나갔다.\n\n\"지루한 추억팔이는 거기까지.\"\n\n베라의 멀쩡한 왼쪽 눈이 살기로 번뜩였다. 그녀는 품에서 고대 문자가 빼곡히 적힌 황금빛 두루마리를 꺼내 들었다.\n\n\"티오, 놈을 묶어. 이 사원의 보물인 '영원의 성배'는 피를 원해. 봉인을 풀려면 싱싱하게 살아있는 제물이 필요하거든.\"\n\n베라가 주문을 영창하기 시작했다. 공간이 뒤틀리며 압도적인 마력이 사원을 진동시켰다. 지금이 아니면 기회는 없다. 티오가 망설이며 주춤거리는 그 찰나의 틈, 리안은 바닥을 박차고 튀어 나갔다. 목표는 티오가 아닌, 주문을 외우고 있는 베라의 무방비한 옆구리였다.\n\n폭풍우 소리보다 더 큰 기합 소리가 사원 내부를 쩌렁쩌렁하게 울렸다.\n\n단검의 서슬 퍼런 날이 베라의 허리춤에 닿기 직전이었다. 승리를 확신한 리안의 눈빛이 매섭게 빛났다. 주문을 외우느라 무방비 상태인 마법사는 근접전에서 취약하다는 것이 정설이었으니까. 하지만 베라는 주문을 멈추지 않았다. 대신 그녀의 입꼬리가 비릿하게 올라갔다.\n\n카앙!\n\n날카로운 금속음과 함께 리안의 손목이 꺾일 듯한 충격을 받았다. 베라의 몸 주변으로 투명한 바람의 장막이 소용돌이치고 있었다. '폭풍의 지팡이'가 가진 자동 방어 기제였다. 튕겨 나간 것은 단검이 아니라 리안이었다. 거센 돌풍이 그의 가슴팍을 걷어찼고, 리안은 바닥을 두세 번 구른 뒤에야 겨우 중심을 잡고 멈춰 섰다.\n\n\"크윽...\"\n\n입안에서 비릿한 피 맛이 났다. 베라는 그제야 주문 영창을 끝내고 천천히 리안을 내려다보았다.\n\n\"순진하긴. 내가 고작 칼부림 하나 못 막을 거라 생각했어? 이 지팡이는 내 의지보다 더 빠르게 반응해.\"\n\n베라가 지팡이를 가볍게 휘두르자, 허공에 떠 있던 푸른 마력들이 뱀처럼 꿈틀거리며 리안의 팔다리를 향해 쇄도했다. 리안이 몸을 비틀어 피하려 했지만, 역부족이었다. 보이지 않는 바람의 사슬이 그의 발목을 휘감아 공중으로 들어 올렸다.\n\n\"윽! 이거 놔!\"\n\n허공에 대롱대롱 매달린 꼴이 된 리안이 발버둥 쳤지만, 사슬은 조여들기만 했다. 베라는 흥미를 잃었다는 듯 시선을 돌려 티오를 바라보았다. 티오는 여전히 덜덜 떨며 망가진 회중시계만 만지작거리고 있었다.\n\n\"티오, 뭘 멍청하게 서 있어? 어서 성배를 가져와. 제물은 내가 손질할 테니까.\"\n\n\"하, 하지만 대장님... 피를 봐야 한다니요. 그냥 마력만 추출하면 되는 거 아니었나요?\"\n\n티오가 울먹이며 항변하자, 베라의 미간이 찌푸려졌다. 그녀는 손가락을 튕겼다. 그러자 리안을 옥죄던 바람의 사슬이 더욱 거세게 조여들며 뼈가 으스러지는 소리를 냈다.\n\n\"으아악!\"\n\n리안의 비명에 티오의 얼굴이 하얗게 질렸다.\n\n\"잘 들어, 꼬마야. '영원의 성배'는 등가교환이야. 영원한 힘을 얻으려면 생명력을 바쳐야 해. 네가 3년 전 그 잿더미 속에서 살아남고 싶어 했던 것처럼, 나도 이 힘이 절실하거든. 그러니까 선택해. 네 손으로 직접 성배를 바칠래, 아니면 저 쥐새끼랑 같이 여기서 묻힐래?\"\n\n베라의 협박은 단순했지만 효과적이었다. 티오는 공포에 질린 눈으로 고통스러워하는 리안을 바라보았다. 그의 머릿속에서 3년 전의 기억이 플래시백처럼 스쳤다. 불타는 마을, 무너지는 지붕, 그리고 멀어지는 리안의 뒷모습. 오해와 진실 사이에서 소년의 마음은 위태로운 줄타기를 하고 있었다.\n\n\"티오! 듣지 마! 저 여자는 널 이용하고 버릴 거야!\"\n\n리안이 핏대를 세우며 소리쳤다. 그 목소리에 티오가 움찔하며 고개를 들었다. 티오의 눈망울에 고여있던 눈물이 뺨을 타고 흘러내렸다. 그는 천천히, 아주 천천히 베라에게서 등을 돌려 제단 쪽으로 걸음을 옮겼다.\n\n\"그래, 착하지.\"\n\n베라가 만족스런 미소를 지으며 리안을 제단 바로 위로 끌고 갔다. 제단 중앙에는 낡고 이끼 낀 돌그릇, '영원의 성배'가 놓여 있었다. 겉보기엔 평범한 돌덩이 같았지만, 그 주변의 공기는 기분 나쁘게 일렁이고 있었다.\n\n베라는 품에서 단도를 꺼내 리안의 손목을 겨누었다.\n\n\"자, 이제 영원한 잠에 들 시간이야, 리안. 네 피가 새로운 시대를 여는 열쇠가 될 거다.\"\n\n차가운 칼날이 리안의 피부에 닿았다. 그 순간이었다.\n\n\"안 돼요!\"\n\n쿵, 하는 소리와 함께 티오가 짊어지고 있던 거대한 짐 가방을 제단 위에 내려놓은 것이 아니라, 있는 힘껏 베라를 향해 던졌다.\n\n\"이 미친 꼬맹이가!\"\n\n베라가 당황하며 지팡이를 들어 가방을 쳐냈지만, 그 묵직한 무게 탓에 중심을 잃고 비틀거렸다. 가방이 터지며 그 안에 들어있던 각종 마법 공구와 폭약들이 바닥으로 쏟아졌다.\n\n\"형! 지금이야! 도망쳐!\"\n\n티오가 리안을 묶고 있는 마법진의 핵을 향해 돌멩이 하나를 정확히 던졌다. 파직, 하는 소리와 함께 리안을 옥죄던 바람의 사슬이 느슨해졌다. 땅으로 떨어진 리안은 거친 숨을 몰아쉬며 바닥에 굴러떨어진 자신의 단검을 낚아챘다. 상황은 다시 원점으로 돌아왔다. 아니, 이제는 2대 1이었다.\n\n리안은 비틀거리는 몸을 일으켜 티오의 앞을 막아섰다. 그의 등은 3년 전처럼 도망치기 위함이 아니라, 이번에는 지키기 위해 티오를 향해 있었다.\n\n\"미안하다, 늦게 와서. 하지만 이번엔 절대 두고 가지 않아.\"\n\n리안의 낮은 읊조림에 티오가 입술을 깨물며 고개를 끄덕였다. 베라가 헝클어진 머리카락을 쓸어 넘기며 싸늘하게 쏘아붙였다.\n\n\"감동적인 형제애네. 좋아, 그럼 둘 다 제물로 바쳐주지. 성배가 아주 기뻐하겠어.\"\n\n그녀의 폭풍의 지팡이 끝에서 아까와는 비교도 안 될 만큼 거대한, 칠흑 같은 뇌전이 엉겨 붙기 시작했다.",
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
    docker logs -f stolink-fastapi-agent
    ```
    You should see "Received analysis task" and eventually "Analysis task completed".
3.  **Webhook Site**: Check your Webhook window. You should receive a `POST` request with the analysis result JSON.

## Troubleshooting

- **Message stuck in queue**: Check if `ai-backend` container is running (`docker ps`).
- **No callback received**: Check Docker logs for errors. Ensure the `callback_url` is accessible from the Docker container (public URLs like webhook.site work fine).
