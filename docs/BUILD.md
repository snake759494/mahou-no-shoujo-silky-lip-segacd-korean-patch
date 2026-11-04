# 빌드

1. 저장소 루트에 원본 `Mahou no Shoujo - Silky Lip (Japan).chd`(SHA-256은 README 표 참고)를 준비하고 `chdman extractcd`로 `work/orig.cue`·`work/orig.bin`을 만듭니다.
2. 루트에 나눔스퀘어 네오(`NanumSquareNeo-bRg/cBd/dEb/eHv.ttf`), `tools/fonts/`에 갈무리(`Galmuri7/9/11/11-Bold.ttf`)를 넣습니다.
3. `python tools/extract.py`로 사용자 디스크에서 원문 목록(`work/strings.json`, `work/tr/uniq.json`)을 만들고, `translation/k*.txt`를 `work/tr/`에 복사합니다.
4. `python tools/build.py`로 `work/test.bin`을 만들고 `chdman createcd`로 CHD를 만듭니다.
5. `xdelta3 -f -0 -S none -D -e -s 원본.chd 결과.chd 패치.xdelta`

`requirements.txt`의 Pillow 외에 numpy가 필요합니다.
