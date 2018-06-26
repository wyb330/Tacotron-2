# -*- coding: utf-8 -*-
import re

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


if __name__ == '__main__':
    print(h2j("대한민국 만세"))
    print(h2j("올해는 2017년 이다."))
    print(h2j("LA에는 많은 한국인들이 살고 있다."))
    print(j2h(h2j("대한민국 만세")))
    print(j2h(h2j("올해는 2017년 이다.")))
    print(j2h(h2j("LA에는 많은 한국인들이 살고 있다.")))
    print(j2h(h2j("2교대 3교대로 전환 되었지만~")))
