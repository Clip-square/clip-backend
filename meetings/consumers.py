import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MeetingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.meeting_id = self.scope['url_route']['kwargs']['meeting_id']
        self.room_group_name = f"meeting_{self.meeting_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "join_meeting":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "user_joined", "username": data["username"]}
            )
        elif action == "start_meeting":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "start_timer"}
            )
        elif action == "pause_meeting":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "pause_timer"}
            )
        elif action == "end_meeting":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "end_timer"}
            )
        elif action == "send_audio":
            # 서버에서 오디오 데이터를 다른 클라이언트에게 전달
            audio_data = data.get("audio_data")
            if audio_data:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "receive_audio", "audio_data": audio_data}
                )

    async def user_joined(self, event):
        await self.send(json.dumps({"action": "user_joined", "username": event["username"]}))

    async def start_timer(self, event):
        await self.send(json.dumps({"action": "start"}))

    async def pause_timer(self, event):
        await self.send(json.dumps({"action": "pause"}))

    async def end_timer(self, event):
        await self.send(json.dumps({"action": "end"}))

    async def receive_audio(self, event):
        # 오디오 데이터를 다른 클라이언트에게 전달
        await self.send(json.dumps({
            "action": "receive_audio",
            "audio_data": event["audio_data"]  # Base64로 인코딩된 음성 데이터
        }))
