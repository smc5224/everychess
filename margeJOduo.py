import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

# 사진을 체스판으로 자르기
def detect_and_crop_chessboard(image_path):
    # 이미지 불러오기
    image = cv2.imread(image_path)
    if image is None:
        print("이미지를 불러올 수 없습니다. 경로를 확인하세요.")
        return None

    # 이미지를 그레이스케일로 변환
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 블러를 적용해 노이즈 줄이기
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 에지 검출 (Canny Edge Detection)
    edges = cv2.Canny(blurred, 50, 150)

    # 윤곽선 찾기
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 가장 큰 사각형 윤곽선을 찾기 (체스판을 가정)
    max_contour = max(contours, key=cv2.contourArea)

    # 체스판 윤곽선을 사각형으로 근사화
    epsilon = 0.02 * cv2.arcLength(max_contour, True)
    approx = cv2.approxPolyDP(max_contour, epsilon, True)

    if len(approx) == 4:  # 사각형인지 확인
        # 사각형의 네 점을 얻어서 정렬
        pts = approx.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")

        # 점을 위쪽 좌우, 아래쪽 좌우 순으로 정렬
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        # 체스판을 정사각형으로 변환 (워핑)
        (tl, tr, br, bl) = rect
        maxWidth = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        maxHeight = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        cropped_chessboard = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

        # 체스판만 잘라낸 이미지 반환
        return cropped_chessboard
    else:
        print("체스판을 인식하지 못했습니다.")
        return None
# 체스판을 8x8로 자르고 리스트로 만들기 ( (i, j) i는 세로축, j는 가로축 / 왼쪽 위부터 0 )
def split_chessboard(image):
    board_size = 8  # 체스판은 8x8
    height, width = image.shape[:2]
    cell_width = width // board_size
    cell_height = height // board_size
    cells = []

    for i in range(board_size):
        row = []
        for j in range(board_size):
            x_start = j * cell_width
            y_start = i * cell_height
            cell = image[y_start:y_start + cell_height, x_start:x_start + cell_width]
            row.append(cell)
        cells.append(row)

    return cells
# 
def compare_cells(cell1, cell2):
    # Grayscale로 변환
    cell1_gray = cv2.cvtColor(cell1, cv2.COLOR_BGR2GRAY)
    cell2_gray = cv2.cvtColor(cell2, cv2.COLOR_BGR2GRAY)

    # 구조적 유사도 계산
    score, _ = ssim(cell1_gray, cell2_gray, full=True)
    return score

turn_count = 1  # 턴을 관리할 변수
board_state = [
    ["BR", "BN", "BB", "BQ", "BK", "BB", "BN", "BR"],  # 백 기물의 첫 번째 줄
    ["BP", "BP", "BP", "BP", "BP", "BP", "BP", "BP"],  # 백 폰의 줄
    [None, None, None, None, None, None, None, None],  # 빈 칸
    [None, None, None, None, None, None, None, None],  # 빈 칸
    [None, None, None, None, None, None, None, None],  # 빈 칸
    [None, None, None, None, None, None, None, None],  # 빈 칸
    ["WP", "WP", "WP", "WP", "WP", "WP", "WP", "WP"],  # 흑 폰의 줄
    ["WR", "WN", "WB", "WQ", "WK", "WB", "WN", "WR"]   # 흑 기물의 첫 번째 줄
]

def detect_moves(initial_image, new_image):

    global board_state  # board_state를 전역 변수로 선언
    global turn_count   # turn_count를 전역 변수로 선언

    initial_board = split_chessboard(initial_image)
    new_board = split_chessboard(new_image)
    moves = []

    for i in range(8):
        for j in range(8):
            similarity = compare_cells(initial_board[i][j], new_board[i][j])

            # SSIM이 0.9 이하이면 말의 이동이 있다고 간주
            if similarity < 0.9:
                moves.append((i, j))  # 이동된 위치 저장

    # 이동이 발생한 칸을 분석하여 어느 칸에서 어느 칸으로 이동했는지 판단
    if len(moves) == 2:
        Acell, Bcell = moves
        piece_A = board_state[Acell[0]][Acell[1]]
        piece_B = board_state[Bcell[0]][Bcell[1]]

        if piece_A is not None and piece_B is None:
            if is_valid_move(piece_A, Acell, Bcell) == True:
                # A에 기물이 있고 B는 비어 있는 경우
                print(f"{piece_A}가 {Acell}에서 {Bcell}로 이동했습니다.")
                board_state[Acell[0]][Acell[1]] = None  # A 위치를 빈칸으로
                board_state[Bcell[0]][Bcell[1]] = piece_A  # B 위치로 이동
            else : 
                print(f"규칙오류 : {piece_A}가 {Acell}에서 {Bcell}로 이동할 수 없습니다.")
                turn_count-=1

        elif piece_A is None and piece_B is not None:
            if is_valid_move(piece_B, Bcell, Acell) == True:
                # B에 기물이 있고 A는 비어 있는 경우
                print(f"{piece_B}가 {Bcell}에서 {Acell}로 이동했습니다.")
                board_state[Bcell[0]][Bcell[1]] = None  # B 위치를 빈칸으로
                board_state[Acell[0]][Acell[1]] = piece_B  # A 위치로 이동
            else : 
                print(f"규칙오류 : {piece_B}가 {Bcell}에서 {Acell}로 이동할 수 없습니다.")
                turn_count-=1
        else:
            if is_valid_move(piece_A, Acell, Bcell) == True:
                # 두 위치 모두 기물이 있는 경우 (기물 잡기 상황)
                if turn_count % 2 != 0:  # 홀수 턴이면 백이 흑을 잡음
                    print(f"백의 {piece_A}가 {Bcell}에서 흑의 {piece_B}를 잡았습니다.")
                else:  # 짝수 턴이면 흑이 백을 잡음
                    print(f"흑의 {piece_A}가 {Bcell}에서 백의 {piece_B}를 잡았습니다.")
                
                board_state[Bcell[0]][Bcell[1]] = piece_A  # B 위치로 A의 기물 이동
                board_state[Acell[0]][Acell[1]] = None  # A 위치를 빈칸으로
            else :

                if turn_count % 2 != 0:  # 홀수 턴이면 백이 흑을 잡음
                    print(f"규칙오류 : 백의 {piece_A}가 {Bcell}에서 흑의 {piece_B}를 잡을 수 없습니다.")
                    turn_count-=1
                else:  # 짝수 턴이면 흑이 백을 잡음
                    print(f"규칙오류 : 흑의 {piece_A}가 {Bcell}에서 백의 {piece_B}를 잡을 수 없습니다.")
                    turn_count-=1
        # 턴 수 증가
        turn_count += 1
    else:
        print("이동을 감지하지 못했습니다. 또는 복수의 이동이 감지되었습니다.")

    # 체스 기물 이동 규칙을 확인하는 함수
def is_valid_move(piece, start, end):
    """
    체스 기물의 이동 규칙을 검사합니다.
    :param piece: 이동하는 기물 (예: 'WP', 'BP', 'WR', 등)
    :param start: 시작 위치 (행, 열)
    :param end: 도착 위치 (행, 열)
    :return: 이동이 규칙에 맞는지 여부 (True / False)
    """
    start_row, start_col = start
    end_row, end_col = end

    # 이동 차이 계산
    row_diff = end_row - start_row
    col_diff = end_col - start_col

    # 백 기물 (대문자로 시작)
    if piece.startswith('W'):
        # 폰
        if piece == 'WP':
            if start_row == 6:  # 초기 위치에서
        # 직진하거나 잡기 이동 추가
                return ((row_diff == -2 and col_diff == 0 and board_state[end_row][end_col] is None) or
                        (row_diff == -1 and col_diff == 0 and board_state[end_row][end_col] is None) or
                        (row_diff == -1 and abs(col_diff) == 1 and board_state[end_row][end_col] is not None))
            else:  # 일반 이동
        # 직진하거나 잡기 이동 추가
                return ((row_diff == -1 and col_diff == 0 and board_state[end_row][end_col] is None) or
                        (row_diff == -1 and abs(col_diff) == 1 and board_state[end_row][end_col] is not None))

        # 룩
        elif piece == 'WR':
            return row_diff == 0 or col_diff == 0
        # 나이트
        elif piece == 'WN':
            return abs(row_diff) == 2 and abs(col_diff) == 1 or abs(row_diff) == 1 and abs(col_diff) == 2
        # 비숍
        elif piece == 'WB':
            return abs(row_diff) == abs(col_diff)
        # 퀸
        elif piece == 'WQ':
            return abs(row_diff) == abs(col_diff) or row_diff == 0 or col_diff == 0
        # 킹
        elif piece == 'WK':
            return abs(row_diff) <= 1 and abs(col_diff) <= 1

    # 흑 기물 (소문자로 시작)
    elif piece.startswith('B'):
        # 폰
        if piece == 'BP':
            if start_row == 1:  # 초기 위치에서
            # 직진하거나 잡기 이동 추가
                return ((row_diff == 2 and col_diff == 0 and board_state[end_row][end_col] is None) or
                        (row_diff == 1 and col_diff == 0 and board_state[end_row][end_col] is None) or
                        (row_diff == 1 and abs(col_diff) == 1 and board_state[end_row][end_col] is not None))
            else:  # 일반 이동
            # 직진하거나 잡기 이동 추가
                
                
                return ((row_diff == 1 and col_diff == 0 and board_state[end_row][end_col] is None) or
                        (row_diff == 1 and abs(col_diff) == 1 and board_state[end_row][end_col] is not None))
        # 룩
        elif piece == 'BR':
            return row_diff == 0 or col_diff == 0
        # 나이트
        elif piece == 'BN':
            return abs(row_diff) == 2 and abs(col_diff) == 1 or abs(row_diff) == 1 and abs(col_diff) == 2
        # 비숍
        elif piece == 'BB':
            return abs(row_diff) == abs(col_diff)
        # 퀸
        elif piece == 'BQ':
            return abs(row_diff) == abs(col_diff) or row_diff == 0 or col_diff == 0
        # 킹
        elif piece == 'BK':
            return abs(row_diff) <= 1 and abs(col_diff) <= 1

def detect_moves_with_rules(initial_image, new_image):
    """
    체스판 이동을 감지하고, 이동 규칙 위반 여부를 검사합니다.
    """
    global board_state  # 체스판 상태를 전역 변수로 가져오기
    global turn_count   # 턴 수를 전역 변수로 가져오기

    # 체스판을 8x8 셀로 나누기
    initial_board = split_chessboard(initial_image)
    new_board = split_chessboard(new_image)
    moves = []  # 이동된 위치를 저장할 리스트

    # 두 이미지의 체스판을 비교하여 이동 위치를 찾기
    for i in range(8):
        for j in range(8):
            similarity = compare_cells(initial_board[i][j], new_board[i][j])

            # SSIM 유사도가 0.9 이하라면 이동 발생으로 간주
            if similarity < 0.9:
                moves.append((i, j))  # 이동 위치 추가

    # 이동된 위치가 두 곳으로 감지된 경우
    if len(moves) == 2:
        Acell, Bcell = moves  # 이동된 두 위치
        piece_A = board_state[Acell[0]][Acell[1]]  # Acell의 기물
        piece_B = board_state[Bcell[0]][Bcell[1]]  # Bcell의 기물

        if piece_A is not None and piece_B is None:
            # A 위치에 기물이 있고 B 위치는 비어있는 경우 (일반 이동)
            if is_valid_move(piece_A, Acell, Bcell):
                print(f"{piece_A}가 {Acell}에서 {Bcell}로 이동했습니다.")
                board_state[Acell[0]][Acell[1]] = None  # A 위치는 빈칸으로 설정
                board_state[Bcell[0]][Bcell[1]] = piece_A  # B 위치로 기물 이동
            else:
                print(f"규칙 위반: {piece_A}가 {Acell}에서 {Bcell}로 이동할 수 없습니다.")

        elif piece_A is None and piece_B is not None:
            # B 위치에 기물이 있고 A 위치는 비어있는 경우 
            print(f"{piece_B}가 {Bcell}에서 {Acell}로 이동했습니다.")

        elif piece_A is not None and piece_B is not None:
            # 두 위치 모두 기물이 있는 경우 (기물 잡기 상황)
            if is_valid_move(piece_A, Acell, Bcell):
                print(f"{piece_A}가 {Acell}에서 {Bcell}로 이동하며 {piece_B}를 잡았습니다.")
                board_state[Acell[0]][Acell[1]] = None  # A 위치는 빈칸으로 설정
                board_state[Bcell[0]][Bcell[1]] = piece_A  # B 위치로 A 기물 이동
            else:
                print(f"규칙 위반: {piece_A}가 {Acell}에서 {Bcell}로 이동할 수 없습니다.")

        # 턴 증가
        turn_count += 1
    else:
        # 이동 감지가 실패하거나 복수의 이동이 감지된 경우
        print("이동을 감지하지 못했습니다. 또는 복수의 이동이 감지되었습니다.")

# 이미지 경로 설정
image1 = 'ChessRg\c1.PNG'  # 업로드한 체스판 이미지 경로 사용
image1 = detect_and_crop_chessboard(image1)
image2 = 'ChessRg\c2.PNG'          # 두 번째 체스판 이미지 경로
image2 = detect_and_crop_chessboard(image2)
image3 = 'ChessRg\c3.PNG'  # 업로드한 체스판 이미지 경로 사용
image3 = detect_and_crop_chessboard(image3)
image4 = 'ChessRg\c4.PNG'          # 두 번째 체스판 이미지 경로
image4 = detect_and_crop_chessboard(image4)
image5 = 'ChessRg\c5.PNG'  # 업로드한 체스판 이미지 경로 사용
image5 = detect_and_crop_chessboard(image5)

# 이동 감지
detect_moves(image1, image2)
detect_moves(image2, image3)
detect_moves(image3, image4)
detect_moves(image4, image5)