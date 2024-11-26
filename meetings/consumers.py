import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MeetingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.meeting_id = self.scope['url_route']['kwargs']['meeting_id']
        self.room_group_name = f"meeting_{self.meeting_id}"

        # WebSocket 연결
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # WebSocket 연결 종료 시 그룹에서 해당 클라이언트 제거
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "send_audio":
            audio_data = data.get("audio_data")
            print("Received audio data:", audio_data)  # 서버에서 받은 오디오 데이터 로그
            if audio_data:
                # 모든 클라이언트에게 오디오 데이터 전송
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "receive_audio",
                        "audio_data": audio_data
                    }
                )

    async def receive_audio(self, event):
        # 다른 클라이언트에게 오디오 데이터를 전달
        await self.send(text_data=json.dumps({
            "action": "receive_audio",
            "audio_data": event["audio_data"]  # Base64로 인코딩된 오디오 데이터
        }))
