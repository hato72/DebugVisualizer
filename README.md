### 実行
```sh
python debug_analizer.py main.txt
```

### 入力例と結果
main.txt
```sh
def add(num1,num2):
  num = 0
  for i in range(5):
    print(num)
    if (num + num2) % 2 == 0:
      num += num1
    else:
      num -= num2
  return num

print(add(5,10))
```
debug_flow.svg

![debug_flow](https://github.com/user-attachments/assets/9dd49601-120f-4fd1-be2d-fa113f87f4c7)
