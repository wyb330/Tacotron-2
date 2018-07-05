# -*- coding: utf-8 -*-
import re
import ast

"""
    초성 중성 종성 분리 하기
    유니코드 한글은 0xAC00 으로부터
    초성 19개, 중상21개, 종성28개로 이루어지고
    이들을 조합한 11,172개의 문자를 갖는다.
    한글코드의 값 = ((초성 * 21) + 중성) * 28 + 종성 + 0xAC00
    (0xAC00은 'ㄱ'의 코드값)
    따라서 다음과 같은 계산 식이 구해진다. 
    유니코드 한글 문자 코드 값이 X일 때,
    초성 = ((X - 0xAC00) / 28) / 21
    중성 = ((X - 0xAC00) / 28) % 21
    종성 = (X - 0xAC00) % 28
    이 때 초성, 중성, 종성의 값은 각 소리 글자의 코드값이 아니라
    이들이 각각 몇 번째 문자인가를 나타내기 때문에 다음과 같이 다시 처리한다.
    초성문자코드 = 초성 + 0x1100 //('ㄱ')
    중성문자코드 = 중성 + 0x1161 // ('ㅏ')
    종성문자코드 = 종성 + 0x11A8 - 1 // (종성이 없는 경우가 있으므로 1을 뺌)
"""
# 유니코드 한글 시작 : 44032, 끝 : 55199
BASE_CODE, CHOSUNG, JUNGSUNG = 44032, 588, 28

# 초성 리스트. 00 ~ 18
CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

# 중성 리스트. 00 ~ 20
JUNGSUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']

# 종성 리스트. 00 ~ 27 + 1(1개 없음)
JONGSUNG_LIST = [' ', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

HANGUEL_LIST = 'ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㄲㄸㅃㅆㅉㅏㅑㅓㅕㅗㅛㅜㅠㅡㅣㅐㅒㅔㅖㅘㅙㅚㅝㅞㅟㅢㄳㄵㄶㄺㄻㄼㄽㄾㄿㅀㅄ'

SYMBOLS = [' ', '~', '#', '.', '?', '!', ',']


def is_hanguel(char):
    return True if char in HANGUEL_LIST else False


def is_korean_text(text):
    for char in text:
        if 44032 < ord(char) < 55199:
            return True
    return False


def is_korean_char(text):
    for char in text:
        if is_hanguel(char):
            return True
    return False


def split_to_jamo(text, cleaners):
    if 'korean_cleaners' in cleaners:
        return h2j(text)
    else:
        return text


def merge_j(jamos):
    if len(jamos) == 3:
        code = CHOSUNG_LIST.index(jamos[0]) * CHOSUNG + \
               JUNGSUNG_LIST.index(jamos[1]) * JUNGSUNG + \
               JONGSUNG_LIST.index(jamos[2])
    else:
        code = CHOSUNG_LIST.index(jamos[0]) * CHOSUNG + \
               JUNGSUNG_LIST.index(jamos[1]) * JUNGSUNG
    code += BASE_CODE
    c = chr(code)
    return c + ' ' if jamos[-1] == ' ' else c


def h2j(text):
    result = list()
    for keyword in text:
        # 한글 여부 check 후 분리
        if re.match('.*[ㄱ-ㅎㅏ-ㅣ가-힣]+.*', keyword) is not None:
            char_code = ord(keyword) - BASE_CODE
            char1 = int(char_code / CHOSUNG)
            result.append(CHOSUNG_LIST[char1])
            char2 = int((char_code - (CHOSUNG * char1)) / JUNGSUNG)
            result.append(JUNGSUNG_LIST[char2])
            char3 = int((char_code - (CHOSUNG * char1) - (JUNGSUNG * char2)))
            # 종성이 있는 경우
            if char3 > 0:
                result.append(JONGSUNG_LIST[char3])
        else:
            result.append(keyword)
    # result
    return "".join(result)


def j2h(text):
    result = list()
    idx = 0
    while idx < len(text):
        c = text[idx]
        if is_hanguel(c):
            if c in CHOSUNG_LIST:
                if idx + 1 < len(text) and text[idx + 1] in JUNGSUNG_LIST:
                    if idx + 2 < len(text) and text[idx + 2] in JONGSUNG_LIST:
                        if (idx + 3 < len(text) and text[idx + 3] in CHOSUNG_LIST + SYMBOLS) or (idx +3 == len(text)):
                            result.append(merge_j(text[idx: idx + 3]))
                            idx += 2
                        else:
                            result.append(merge_j(text[idx: idx + 2]))
                            idx += 1
                    else:
                        result.append(merge_j(text[idx: idx + 2]))
                        idx += 1
        else:
            result.append(c)
        idx += 1

    return ''.join(result)


def korean_numbers(text):
    text = normalize_number(text)
    return text


# Code from https://github.com/carpedm20/multi-speaker-tacotron-tensorflow/blob/master/text/korean.py
number_checker = "([+-]?[1-9][\d,]*)[\.]?\d*"
count_checker = "(시|명|가지|살|마리|포기|송이|수|톨|통|점|개|벌|척|채|다발|그루|자루|줄|켤레|그릇|잔|마디|상자|사람|곡|병|판)"
num_to_kor1 = [""] + list("일이삼사오육칠팔구")
num_to_kor2 = [""] + list("만억조경해")
num_to_kor3 = [""] + list("십백천")

count_to_kor1 = [""] + ["한","두","세","네","다섯","여섯","일곱","여덟","아홉"]

count_tenth_dict = {
        "십": "열",
        "두십": "스물",
        "세십": "서른",
        "네십": "마흔",
        "다섯십": "쉰",
        "여섯십": "예순",
        "일곱십": "일흔",
        "여덟십": "여든",
        "아홉십": "아흔",
}

num_to_kor = {
        '0': '영',
        '1': '일',
        '2': '이',
        '3': '삼',
        '4': '사',
        '5': '오',
        '6': '육',
        '7': '칠',
        '8': '팔',
        '9': '구',
}

unit_to_kor1 = {
        '%': '퍼센트',
        'cm': '센치미터',
        'mm': '밀리미터',
        'km': '킬로미터',
        'kg': '킬로그람',
}
unit_to_kor2 = {
        'm': '미터',
}

upper_to_kor = {
        'A': '에이',
        'B': '비',
        'C': '씨',
        'D': '디',
        'E': '이',
        'F': '에프',
        'G': '지',
        'H': '에이치',
        'I': '아이',
        'J': '제이',
        'K': '케이',
        'L': '엘',
        'M': '엠',
        'N': '엔',
        'O': '오',
        'P': '피',
        'Q': '큐',
        'R': '알',
        'S': '에스',
        'T': '티',
        'U': '유',
        'V': '브이',
        'W': '더블유',
        'X': '엑스',
        'Y': '와이',
        'Z': '지',
}


def normalize_with_dictionary(text, dic):
    if any(key in text for key in dic.keys()):
        pattern = re.compile('|'.join(re.escape(key) for key in dic.keys()))
        return pattern.sub(lambda x: dic[x.group()], text)
    else:
        return text


def normalize_number(text):
    text = normalize_with_dictionary(text, unit_to_kor1)
    text = normalize_with_dictionary(text, unit_to_kor2)
    text = re.sub(number_checker + count_checker,
            lambda x: number_to_korean(x, True), text)
    text = re.sub(number_checker,
            lambda x: number_to_korean(x, False), text)
    return text


def number_to_korean(num_str, is_count=False):
    if is_count:
        num_str, unit_str = num_str.group(1), num_str.group(2)
    else:
        num_str, unit_str = num_str.group(), ""

    num_str = num_str.replace(',', '')
    num = ast.literal_eval(num_str)

    if num == 0:
        return "영"

    check_float = num_str.split('.')
    if len(check_float) == 2:
        digit_str, float_str = check_float
    elif len(check_float) >= 3:
        raise Exception(" [!] Wrong number format")
    else:
        digit_str, float_str = check_float[0], None

    if is_count and float_str is not None:
        raise Exception(" [!] `is_count` and float number does not fit each other")

    digit = int(digit_str)

    if digit_str.startswith("-"):
        digit, digit_str = abs(digit), str(abs(digit))

    kor = ""
    size = len(str(digit))
    tmp = []

    for i, v in enumerate(digit_str, start=1):
        v = int(v)

        if v != 0:
            if is_count:
                tmp += count_to_kor1[v]
            else:
                tmp += num_to_kor1[v]

            tmp += num_to_kor3[(size - i) % 4]

        if (size - i) % 4 == 0 and len(tmp) != 0:
            kor += "".join(tmp)
            tmp = []
            kor += num_to_kor2[int((size - i) / 4)]

    if is_count:
        if kor.startswith("한") and len(kor) > 1:
            kor = kor[1:]

        if any(word in kor for word in count_tenth_dict):
            kor = re.sub(
                '|'.join(count_tenth_dict.keys()),
                lambda x: count_tenth_dict[x.group()], kor)

    if not is_count and kor.startswith("일") and len(kor) > 1:
        kor = kor[1:]

    if float_str is not None:
        kor += "쩜 "
        kor += re.sub('\d', lambda x: num_to_kor[x.group()], float_str)

    if num_str.startswith("+"):
        kor = "플러스 " + kor
    elif num_str.startswith("-"):
        kor = "마이너스 " + kor

    return kor + unit_str


if __name__ == '__main__':
    print(korean_numbers("대한민국 만세"))
    print(korean_numbers("올해는 2017년 이다."))
    print(korean_numbers("LA에는 많은 한국인들이 살고 있다."))
    print(j2h(korean_numbers("대한민국 만세")))
    print(j2h(korean_numbers("올해는 2017년 이다.")))
    print(j2h(korean_numbers("그 친구는 05학번이다.")))
    print(j2h(korean_numbers("LA에는 많은 한국인들이 살고 있다.")))
    print(j2h(korean_numbers("2교대 3교대로 전환 되었지만~")))
    print(j2h(korean_numbers("면적은 대한민국 국토의 0.6%이지만, 약 980만 명이 살고 있어서 인구밀도가 높다.")))
    print(j2h(korean_numbers("동서 간의 거리는 36.78 km, 남북 간의 거리는 30.3 km이며, 넓이는 605.25 km²이다.")))
    print(j2h(korean_numbers("시청 소재지는 중구이며, 25개의 자치구로 이루어져 있다.")))
    print(j2h(korean_numbers("1986년 아시안 게임, 1988년 하계 올림픽, 2010년 서울 G20 정상회의를 개최한 국제적인 도시이다.")))
    print(j2h(korean_numbers("그녀의 딸은 올해 8살이다.")))
