"""
ELO rating calculation for Gomoku
"""


def calculate_elo_change(winner_elo: int, loser_elo: int, k_factor: int = 32) -> tuple:
    """
    Tính toán thay đổi điểm ELO cho cả người thắng và người thua.
    
    Args:
        winner_elo: ELO hiện tại của người thắng
        loser_elo: ELO hiện tại của người thua
        k_factor: Hệ số K (mặc định 32)
    
    Returns:
        (winner_change, loser_change): Tuple chứa điểm thay đổi cho cả 2
    """
    # Tính xác suất thắng kỳ vọng
    expected_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    expected_loser = 1 / (1 + 10 ** ((winner_elo - loser_elo) / 400))
    
    # Tính điểm thay đổi (S = 1 cho thắng, 0 cho thua)
    winner_change = round(k_factor * (1 - expected_winner))
    loser_change = round(k_factor * (0 - expected_loser))
    
    return winner_change, loser_change


def calculate_elo_draw(player1_elo: int, player2_elo: int, k_factor: int = 32) -> tuple:
    """
    Tính toán thay đổi điểm ELO khi hòa.
    
    Args:
        player1_elo: ELO của người chơi 1
        player2_elo: ELO của người chơi 2
        k_factor: Hệ số K (mặc định 32)
    
    Returns:
        (player1_change, player2_change): Tuple chứa điểm thay đổi
    """
    # Tính xác suất thắng kỳ vọng
    expected_1 = 1 / (1 + 10 ** ((player2_elo - player1_elo) / 400))
    expected_2 = 1 / (1 + 10 ** ((player1_elo - player2_elo) / 400))
    
    # Tính điểm thay đổi (S = 0.5 cho hòa)
    player1_change = round(k_factor * (0.5 - expected_1))
    player2_change = round(k_factor * (0.5 - expected_2))
    
    return player1_change, player2_change
