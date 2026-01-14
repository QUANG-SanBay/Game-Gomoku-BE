from rest_framework import serializers

from .models import Match, Room


class RoomSerializer(serializers.ModelSerializer):
    room_id = serializers.IntegerField(source="id", read_only=True)
    host_name = serializers.CharField(source="host.username", read_only=True)
    player_2_name = serializers.CharField(source="player_2.username", read_only=True)
    current_players = serializers.IntegerField(read_only=True)
    has_password = serializers.BooleanField(read_only=True)

    class Meta:
        model = Room
        fields = [
            "room_id",
            "room_name",
            "host_name",
            "player_2_name",
            "status",
            "board_size",
            "current_players",
            "has_password",
            "password",
        ]
        extra_kwargs = {
            "password": {"write_only": True, "required": False, "allow_null": True, "allow_blank": True},
            "board_size": {"required": False},
        }

    def create(self, validated_data):
        validated_data["host"] = self.context["request"].user
        return super().create(validated_data)


class MatchHistorySerializer(serializers.Serializer):
    match_id = serializers.IntegerField()
    opponent = serializers.CharField()
    result = serializers.CharField()
    time = serializers.DateTimeField()

    @staticmethod
    def from_match(match: Match, user) -> dict:
        # Determine opponent
        opponent_user = match.player_o if match.player_x == user else match.player_x
        # Determine result
        if match.end_time is None:
            result = "ongoing"
        elif match.winner is None:
            result = "draw"
        elif match.winner_id == user.id:
            result = "win"
        else:
            result = "loss"
        return {
            "match_id": match.id,
            "opponent": opponent_user.username,
            "result": result,
            "time": match.end_time or match.start_time,
        }
