"""
Game logic for Gomoku (5 in a row)
"""


def check_winner(board: list, row: int, col: int, player: str) -> bool:
    """
    Kiểm tra xem người chơi đã thắng hay chưa sau nước đi tại (row, col).
    board: list 2D, board[row][col] = 'X', 'O', hoặc None
    player: 'X' hoặc 'O'
    """
    size = len(board)
    directions = [
        (0, 1),   # Ngang
        (1, 0),   # Dọc
        (1, 1),   # Chéo chính
        (1, -1),  # Chéo phụ
    ]
    
    for dr, dc in directions:
        count = 1  # Đếm ô hiện tại
        
        # Đếm về phía trước
        r, c = row + dr, col + dc
        while 0 <= r < size and 0 <= c < size and board[r][c] == player:
            count += 1
            r += dr
            c += dc
        
        # Đếm về phía sau
        r, c = row - dr, col - dc
        while 0 <= r < size and 0 <= c < size and board[r][c] == player:
            count += 1
            r -= dr
            c -= dc
        
        if count >= 5:
            return True
    
    return False


def is_board_full(board: list) -> bool:
    """Kiểm tra bàn cờ đã đầy chưa (hòa)."""
    for row in board:
        if None in row:
            return False
    return True


def validate_move(board: list, row: int, col: int) -> bool:
    """Kiểm tra nước đi có hợp lệ không."""
    size = len(board)
    if not (0 <= row < size and 0 <= col < size):
        return False
    return board[row][col] is None
