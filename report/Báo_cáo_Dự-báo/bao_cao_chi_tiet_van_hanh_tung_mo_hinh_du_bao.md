# Báo cáo chi tiết cách vận hành các mô hình dự báo doanh thu

## 1. Mục tiêu của bài toán dự báo

Bài toán dự báo trong dự án nhằm ước tính `Doanh thu thuần` theo tháng, cụ thể là dự báo doanh thu từ tháng 1 đến tháng 5 năm 2026. Mô hình không sử dụng dữ liệu năm 2026 để huấn luyện, mà chỉ học từ dữ liệu lịch sử giai đoạn 2023-2025. Sau khi có kết quả dự báo, doanh thu dự báo được dùng làm kịch bản nền để so sánh với doanh thu thực tế năm 2026.

Nói cách khác, mô hình trả lời câu hỏi: nếu doanh nghiệp tiếp tục vận hành theo xu hướng lịch sử trước đó, doanh thu đầu năm 2026 có thể đạt khoảng bao nhiêu. Từ kết quả này, dự án có thể đánh giá doanh thu thực tế năm 2026 đang cao hơn hay thấp hơn so với mức kỳ vọng theo xu hướng cũ.

## 2. Cách biến dữ liệu đầu vào thành input của mô hình

Dữ liệu ban đầu là dữ liệu bán hàng chi tiết trong bảng `sales_final.csv`. Mỗi dòng dữ liệu gốc thường tương ứng với một giao dịch, một chứng từ hoặc một dòng sản phẩm trong đơn hàng. Tuy nhiên, bài toán dự báo được xây dựng ở cấp tháng, nên dữ liệu giao dịch cần được tổng hợp lại thành bảng dữ liệu tháng trước khi đưa vào mô hình.

Trước hết, mô hình lọc dữ liệu giai đoạn 2023-2025 để làm dữ liệu lịch sử. Dữ liệu năm 2026 được giữ riêng, không dùng để huấn luyện, nhằm tránh việc mô hình học trước thông tin của giai đoạn cần đánh giá.

Sau đó, dữ liệu được gom theo `Năm`, `Tháng` và `Quý`. Mỗi dòng sau khi xử lý đại diện cho một tháng kinh doanh. Các chỉ tiêu được tạo như sau:

| Chỉ tiêu | Cách tạo |
|---|---|
| Doanh thu thuần | Tổng doanh thu thuần trong tháng |
| Doanh số | Tổng doanh số trong tháng |
| Chiết khấu | Tổng chiết khấu trong tháng |
| Số lượng | Tổng số lượng bán ra trong tháng |
| Khối lượng KG | Tổng khối lượng bán ra trong tháng |
| Số đơn hàng | Đếm số chứng từ duy nhất trong tháng |
| Số khách hàng | Đếm số mã khách hàng duy nhất trong tháng |
| Số sản phẩm | Đếm số mã sản phẩm duy nhất trong tháng |

Biến mục tiêu của mô hình là `Doanh thu thuần`. Đây là giá trị mô hình cần dự báo. Doanh thu thuần được chọn vì phản ánh doanh thu sau khi đã tính đến chiết khấu và các khoản điều chỉnh, phù hợp hơn để đánh giá kết quả kinh doanh thực tế.

Bộ input cuối cùng đưa vào mô hình gồm 15 biến:

```text
Tháng
Quý
Chỉ số thời gian
Số lượng
Khối lượng KG
Số đơn hàng
Số khách hàng
Số sản phẩm
Tỷ lệ chiết khấu
Giá trị TB/đơn
Tháng_sin
Tháng_cos
Doanh thu trễ 1 tháng
Doanh thu trễ 12 tháng
Doanh thu TB 3 tháng trước
```

Các biến thời gian như `Tháng`, `Quý`, `Chỉ số thời gian`, `Tháng_sin`, `Tháng_cos` giúp mô hình nhận biết xu hướng và mùa vụ. Trong đó, `Tháng_sin` và `Tháng_cos` giúp biểu diễn tháng theo chu kỳ 12 tháng, tránh việc mô hình hiểu sai rằng tháng 12 và tháng 1 cách xa nhau.

Các biến vận hành như `Số lượng`, `Khối lượng KG`, `Số đơn hàng`, `Số khách hàng`, `Số sản phẩm` phản ánh quy mô hoạt động bán hàng. Khi các biến này tăng hoặc giảm, doanh thu thường cũng thay đổi theo.

Các biến giá trị như `Tỷ lệ chiết khấu` và `Giá trị TB/đơn` giúp mô hình hiểu chất lượng doanh thu. `Tỷ lệ chiết khấu` cho biết mức giảm trừ doanh số, còn `Giá trị TB/đơn` cho biết trung bình mỗi đơn hàng tạo ra bao nhiêu doanh thu.

Các biến doanh thu trễ gồm `Doanh thu trễ 1 tháng`, `Doanh thu trễ 12 tháng` và `Doanh thu TB 3 tháng trước`. Nhóm biến này rất quan trọng trong dữ liệu chuỗi thời gian vì doanh thu hiện tại thường chịu ảnh hưởng từ doanh thu tháng gần nhất, doanh thu cùng kỳ năm trước và xu hướng ngắn hạn của vài tháng gần đây.

## 3. Lựa chọn mô hình và cách vận hành các mô hình

Sau khi dữ liệu được biến đổi thành bảng dữ liệu tháng, tất cả các mô hình đều sử dụng cùng một bộ input và cùng một biến mục tiêu. Sự khác nhau giữa các mô hình nằm ở cách chúng học mối quan hệ giữa input và doanh thu.

Quy trình vận hành chung gồm các bước:

1. Chuẩn bị bộ dữ liệu đầu vào gồm 15 biến giải thích và biến mục tiêu `Doanh thu thuần`.
2. Chia dữ liệu theo thời gian, trong đó train là dữ liệu đến hết năm 2024 và test là tháng 1 đến tháng 5 năm 2025.
3. Đưa dữ liệu train vào từng mô hình để mô hình học quy luật giữa các biến đầu vào và doanh thu.
4. Dùng mô hình đã học để dự báo doanh thu trên tập test.
5. So sánh doanh thu dự báo với doanh thu thực tế trên tập test.
6. Tính các chỉ số MAE, MAPE và R2 cho từng mô hình.
7. Chọn mô hình có MAPE thấp nhất để dự báo tháng 1 đến tháng 5 năm 2026.

Việc chia train/test theo thời gian là rất quan trọng. Nếu chia ngẫu nhiên, dữ liệu của tương lai có thể bị đưa vào tập train, khiến kết quả đánh giá không còn đúng bản chất dự báo. Với cách chia hiện tại, mô hình phải học từ quá khứ để dự báo giai đoạn sau, gần với tình huống thực tế hơn.

Khi dự báo năm 2026, hệ thống không lấy trực tiếp doanh thu 2026 làm input. Thay vào đó, input năm 2026 được tạo từ dữ liệu cùng kỳ năm 2025 và điều chỉnh theo xu hướng tăng trưởng lịch sử. Các biến trễ được cập nhật tuần tự: dự báo của tháng trước sẽ được dùng để tạo input cho tháng sau. Nhờ vậy, kết quả dự báo có tính liên tục theo chuỗi thời gian.

### 3.1. Cách vận hành của mô hình Ridge Regression

Ridge Regression là mô hình hồi quy tuyến tính có regularization. Mô hình này giả định rằng doanh thu có thể được ước tính bằng cách cộng tác động của nhiều biến đầu vào lại với nhau. Mỗi biến đầu vào sẽ có một trọng số riêng, thể hiện mức độ và chiều ảnh hưởng của biến đó đến doanh thu.

Về mặt ý tưởng, Ridge học một công thức dạng:

```text
Doanh thu dự báo =
w1 * Tháng
+ w2 * Quý
+ w3 * Chỉ số thời gian
+ ...
+ w15 * Doanh thu TB 3 tháng trước
+ hệ số chặn
```

Trong công thức này, `w1`, `w2`, ..., `w15` là các trọng số mô hình học được từ dữ liệu. Nếu một biến có quan hệ dương với doanh thu, trọng số của biến đó có xu hướng dương. Nếu một biến có quan hệ âm với doanh thu, trọng số có thể âm. Ví dụ, số đơn hàng tăng thường làm doanh thu tăng, còn tỷ lệ chiết khấu tăng có thể làm doanh thu thuần giảm.

Điểm quan trọng của Ridge là mô hình không chỉ tìm công thức khớp dữ liệu train, mà còn phạt các trọng số quá lớn. Cơ chế này gọi là regularization. Nhờ đó, Ridge tránh việc phụ thuộc quá mạnh vào một vài biến hoặc học quá sát các biến động bất thường trong dữ liệu.

Trong bài toán này, trước khi đưa dữ liệu vào Ridge, các biến đầu vào được chuẩn hóa bằng `StandardScaler`. Lý do là các biến có thang đo rất khác nhau: tỷ lệ chiết khấu là số nhỏ, số lượng có thể là hàng chục nghìn, còn doanh thu trễ có thể là hàng tỷ. Chuẩn hóa giúp các biến được đưa về cùng thang đo, để việc học trọng số công bằng và ổn định hơn.

Quy trình vận hành cụ thể của Ridge:

1. Nhận bảng input gồm 15 biến.
2. Chuẩn hóa toàn bộ biến đầu vào về cùng thang đo.
3. Học trọng số tuyến tính của từng biến trên tập train.
4. Dùng công thức đã học để dự báo doanh thu tập test.
5. So sánh dự báo với thực tế và tính MAE, MAPE, R2.
6. Nếu MAPE thấp nhất, mô hình được chọn để dự báo 2026.

Ridge phù hợp với dữ liệu của dự án vì số quan sát theo tháng không nhiều. Với dữ liệu nhỏ, mô hình quá phức tạp có thể học nhiễu, trong khi Ridge đơn giản hơn và có regularization nên thường ổn định hơn. Kết quả thực tế cũng cho thấy Ridge đạt MAPE thấp nhất trong các mô hình được thử nghiệm.

### 3.2. Cách vận hành của mô hình Random Forest

Random Forest là mô hình tập hợp nhiều cây quyết định. Một cây quyết định hoạt động bằng cách chia dữ liệu thành nhiều nhánh dựa trên điều kiện của các biến đầu vào. Ví dụ, cây có thể chia dữ liệu theo tháng, theo doanh thu cùng kỳ năm trước, theo số đơn hàng hoặc theo giá trị trung bình mỗi đơn.

Nếu chỉ dùng một cây quyết định, mô hình dễ bị overfit vì cây có thể chia dữ liệu quá chi tiết và học thuộc các trường hợp đặc biệt trong tập train. Random Forest khắc phục bằng cách tạo ra nhiều cây quyết định khác nhau, sau đó lấy trung bình kết quả dự báo của tất cả các cây.

Trong Random Forest, mỗi cây không học y hệt nhau. Mỗi cây được huấn luyện trên một mẫu dữ liệu khác nhau và có thể xem xét một tập biến khác nhau khi chia nhánh. Điều này giúp các cây có góc nhìn đa dạng hơn. Khi kết hợp nhiều cây, sai số riêng của từng cây có xu hướng được giảm bớt.

Quy trình vận hành của Random Forest trong bài:

1. Nhận bảng input gồm 15 biến.
2. Tạo nhiều bộ dữ liệu con từ tập train.
3. Huấn luyện nhiều cây quyết định trên các bộ dữ liệu con đó.
4. Mỗi cây học các quy luật dạng điều kiện, ví dụ doanh thu cùng kỳ cao, số đơn hàng cao, hoặc tháng thuộc mùa bán tốt.
5. Khi dự báo một tháng, tất cả các cây cùng đưa ra dự báo.
6. Dự báo cuối cùng là trung bình dự báo của các cây.
7. Kết quả được so sánh với thực tế để tính MAE, MAPE, R2.

Trong dự án, Random Forest dùng 300 cây quyết định và giới hạn mỗi nút lá có ít nhất 2 quan sát. Việc này giúp mô hình không chia quá nhỏ dữ liệu.

Ưu điểm của Random Forest là có thể học quan hệ phi tuyến. Ví dụ, tác động của số đơn hàng đến doanh thu có thể khác nhau giữa tháng cao điểm và tháng thấp điểm. Tuy nhiên, hạn chế của Random Forest trong bài này là dữ liệu theo tháng khá ít. Khi số quan sát ít, nhiều cây quyết định có thể không có đủ dữ liệu để học quy luật ổn định. Vì vậy, kết quả MAPE của Random Forest cao hơn Ridge.

### 3.3. Cách vận hành của mô hình Gradient Boosting

Gradient Boosting cũng sử dụng cây quyết định, nhưng cách học khác Random Forest. Random Forest tạo nhiều cây tương đối độc lập rồi lấy trung bình. Gradient Boosting lại tạo cây theo thứ tự nối tiếp, trong đó mỗi cây mới tập trung sửa phần sai số của các cây trước.

Cách vận hành có thể hiểu như sau: ban đầu mô hình đưa ra một dự báo đơn giản. Sau đó, mô hình tính xem dự báo đó đang sai ở đâu. Cây tiếp theo không học lại toàn bộ từ đầu, mà học phần sai số còn lại. Quá trình này lặp nhiều lần, mỗi cây mới bổ sung thêm một phần điều chỉnh để dự báo ngày càng gần thực tế hơn.

Ví dụ, nếu mô hình ban đầu dự báo thấp hơn thực tế ở các tháng có doanh thu cùng kỳ cao, cây tiếp theo có thể học rằng khi `Doanh thu trễ 12 tháng` cao thì cần điều chỉnh dự báo tăng lên. Nếu mô hình tiếp tục sai ở các tháng có số đơn hàng thấp, cây sau nữa có thể học thêm quy luật liên quan đến `Số đơn hàng`.

Quy trình vận hành của Gradient Boosting:

1. Nhận bảng input gồm 15 biến.
2. Tạo dự báo ban đầu cho doanh thu.
3. Tính sai số giữa dự báo và doanh thu thực tế.
4. Huấn luyện một cây nhỏ để học phần sai số đó.
5. Cộng phần điều chỉnh của cây mới vào dự báo hiện tại.
6. Lặp lại quá trình qua nhiều cây.
7. Dự báo cuối cùng là tổng hợp kết quả của toàn bộ chuỗi cây.
8. Đánh giá kết quả bằng MAE, MAPE và R2.

Ưu điểm của Gradient Boosting là khả năng học các quan hệ phức tạp và các tương tác giữa biến đầu vào. Tuy nhiên, do mô hình học tuần tự để sửa sai, nếu dữ liệu ít hoặc có tháng bất thường, mô hình có thể học cả những biến động nhiễu. Trong bài này, Gradient Boosting có MAPE cao hơn Ridge, nên không được chọn làm mô hình cuối.

### 3.4. Cách vận hành của mô hình XGBoost

XGBoost là phiên bản nâng cao của Gradient Boosting. Mô hình này cũng học theo cơ chế boosting, nghĩa là nhiều cây quyết định được xây dựng tuần tự để sửa sai cho nhau. Tuy nhiên, XGBoost có thêm nhiều cơ chế tối ưu để tăng tốc độ học, kiểm soát độ phức tạp và giảm overfit.

Trong dự án, XGBoost được sử dụng nếu môi trường có cài thư viện `xgboost`. Mô hình được cấu hình với các tham số:

```text
n_estimators = 300
learning_rate = 0.05
max_depth = 2
subsample = 0.9
colsample_bytree = 0.9
objective = reg:squarederror
random_state = 42
```

Các tham số này ảnh hưởng trực tiếp đến cách mô hình vận hành. `n_estimators = 300` nghĩa là mô hình xây dựng 300 cây. `learning_rate = 0.05` nghĩa là mỗi cây chỉ đóng góp một phần nhỏ vào kết quả cuối, giúp mô hình học chậm và ổn định hơn. `max_depth = 2` giới hạn độ sâu của cây, giúp mỗi cây không quá phức tạp. `subsample = 0.9` và `colsample_bytree = 0.9` giúp mỗi cây chỉ dùng một phần dữ liệu và một phần biến đầu vào, từ đó giảm nguy cơ học thuộc dữ liệu train.

Quy trình vận hành của XGBoost:

1. Nhận bảng input gồm 15 biến.
2. Tạo cây đầu tiên để đưa ra dự báo ban đầu.
3. Tính sai số còn lại giữa dự báo và thực tế.
4. Tạo cây tiếp theo để sửa phần sai số đó.
5. Lặp lại quá trình qua nhiều cây, nhưng mỗi cây chỉ đóng góp một lượng nhỏ nhờ `learning_rate`.
6. Kiểm soát độ phức tạp của cây bằng `max_depth`, `subsample` và `colsample_bytree`.
7. Kết hợp kết quả của 300 cây để tạo dự báo cuối cùng.
8. Đánh giá dự báo bằng MAE, MAPE và R2.

XGBoost thường mạnh trong các bài toán dữ liệu bảng vì có thể học quan hệ phi tuyến và tương tác giữa nhiều biến. Tuy nhiên, trong bài này dữ liệu theo tháng không nhiều. Khi số quan sát hạn chế, mô hình phức tạp chưa chắc tốt hơn, vì nó có thể học cả những dao động đặc thù của tập train. Do đó, XGBoost có kết quả tốt hơn một số mô hình cây khác nhưng vẫn kém Ridge theo MAPE.

## 4. Cách tạo input cho dự báo năm 2026

Sau khi chọn được mô hình tốt nhất, hệ thống cần tạo bộ input cho các tháng cần dự báo trong năm 2026. Vì năm 2026 là giai đoạn tương lai trong kịch bản dự báo, nhiều biến đầu vào chưa có sẵn và phải được ước tính từ dữ liệu lịch sử.

Nguyên tắc đầu tiên là lấy dữ liệu cùng kỳ năm 2025 làm nền. Để dự báo tháng 1 đến tháng 5 năm 2026, hệ thống lấy dữ liệu tháng 1 đến tháng 5 năm 2025 làm bộ khung ban đầu. Cách này giúp giữ lại đặc điểm mùa vụ của từng tháng. Ví dụ, input nền của tháng 3/2026 được lấy từ đặc điểm vận hành của tháng 3/2025, vì hai tháng này có cùng vị trí mùa vụ trong năm.

Nguyên tắc thứ hai là điều chỉnh các biến vận hành theo xu hướng tăng trưởng lịch sử từ năm 2023 đến năm 2025. Các biến dạng tổng như `Số lượng`, `Khối lượng KG` và `Số đơn hàng` được điều chỉnh theo hệ số tăng trưởng bình quân năm. Các biến dạng trung bình hoặc đếm duy nhất như `Số khách hàng`, `Số sản phẩm` và `Giá trị TB/đơn` được tính theo cách phù hợp với bản chất từng biến, tránh cộng gộp sai ý nghĩa.

Riêng `Tỷ lệ chiết khấu` không dùng hệ số tăng trưởng nhân, vì đây là biến dạng tỷ lệ. Thay vào đó, hệ thống dùng mức chênh lệch điểm tỷ lệ giữa năm 2023 và 2025 để điều chỉnh cho năm 2026. Cách này giúp biến tỷ lệ chiết khấu dễ diễn giải hơn và tránh tạo ra giá trị quá cực đoan.

Nguyên tắc thứ ba là cập nhật các biến doanh thu trễ theo trình tự thời gian. Với tháng 1/2026, biến `Doanh thu trễ 1 tháng` lấy từ doanh thu tháng 12/2025. Sau khi mô hình dự báo xong tháng 1/2026, kết quả dự báo này được đưa vào lịch sử tạm thời để làm `Doanh thu trễ 1 tháng` cho tháng 2/2026. Quy trình tiếp tục tương tự cho tháng 3, tháng 4 và tháng 5.

Biến `Doanh thu trễ 12 tháng` của từng tháng năm 2026 được lấy từ doanh thu cùng tháng năm 2025. Ví dụ, tháng 4/2026 dùng doanh thu tháng 4/2025 làm doanh thu trễ 12 tháng. Biến `Doanh thu TB 3 tháng trước` cũng được cập nhật tuần tự bằng cách lấy trung bình 3 tháng gần nhất, bao gồm cả doanh thu thực tế quá khứ và doanh thu dự báo vừa sinh ra.

Nhờ cách tạo input này, dự báo năm 2026 không phải là việc sao chép nguyên dữ liệu năm 2025, mà là một bộ dữ liệu tương lai có điều chỉnh theo xu hướng lịch sử và vẫn giữ được cấu trúc mùa vụ. Đồng thời, việc cập nhật biến trễ tuần tự giúp các tháng dự báo có liên kết với nhau, phù hợp với bản chất chuỗi thời gian của doanh thu.

## 5. Output các mô hình và cách tính chỉ số đánh giá

Output trực tiếp của mỗi mô hình là `Doanh thu dự báo` cho từng tháng trong tập kiểm tra. Sau đó, hệ thống so sánh doanh thu dự báo với doanh thu thực tế để đánh giá mô hình.

Với mỗi tháng trong tập test, ta có:

```text
y thực tế = Doanh thu thuần thực tế
y dự báo = Doanh thu do mô hình dự báo
Sai số = y thực tế - y dự báo
```

Từ các giá trị này, hệ thống tính ba chỉ số chính: MAE, MAPE và R2.

### 5.1. Công thức và ý nghĩa của MAE

MAE là sai số tuyệt đối trung bình. Công thức:

```text
MAE = trung bình |y thực tế - y dự báo|
```

Trong công thức này, hệ thống lấy chênh lệch giữa doanh thu thực tế và doanh thu dự báo của từng tháng, sau đó lấy giá trị tuyệt đối để mọi sai số đều là số dương. Cuối cùng, các sai số tuyệt đối được lấy trung bình.

Công thức này tạo ra ý nghĩa “mô hình lệch trung bình bao nhiêu tiền mỗi tháng” vì nó đo trực tiếp khoảng cách giữa giá trị thực tế và giá trị dự báo theo cùng đơn vị với doanh thu. Nếu doanh thu được tính bằng đồng, MAE cũng có đơn vị là đồng.

Ví dụ, nếu một tháng thực tế đạt 4 tỷ và mô hình dự báo 4,3 tỷ, sai số tuyệt đối là 300 triệu. Nếu tháng khác thực tế đạt 3 tỷ và mô hình dự báo 2,8 tỷ, sai số tuyệt đối là 200 triệu. MAE sẽ lấy trung bình các mức lệch này để cho biết mức sai số tiền tệ điển hình của mô hình.

Trong kết quả của dự án, Ridge có:

```text
MAE = 304.208.076
```

Điều này có nghĩa là trên tập test tháng 1 đến tháng 5 năm 2025, mô hình Ridge dự báo lệch trung bình khoảng 304 triệu đồng mỗi tháng.

### 5.2. Công thức và ý nghĩa của MAPE

MAPE là sai số phần trăm tuyệt đối trung bình. Công thức:

```text
MAPE = trung bình |y thực tế - y dự báo| / y thực tế
```

Nếu nhân kết quả với 100, ta có MAPE dưới dạng phần trăm.

MAPE có ý nghĩa “mô hình lệch trung bình bao nhiêu phần trăm so với thực tế” vì công thức lấy sai số tuyệt đối chia cho giá trị thực tế. Việc chia cho doanh thu thực tế giúp chuẩn hóa sai số theo quy mô của từng tháng.

Ví dụ, cùng lệch 500 triệu nhưng ý nghĩa sẽ khác nhau:

```text
Tháng A: thực tế 5 tỷ, lệch 500 triệu -> sai số 10%
Tháng B: thực tế 1 tỷ, lệch 500 triệu -> sai số 50%
```

Nếu chỉ nhìn bằng tiền, hai tháng đều lệch 500 triệu. Nhưng nếu nhìn theo tỷ lệ, tháng B bị lệch nghiêm trọng hơn nhiều vì sai số chiếm một nửa doanh thu thực tế. Vì vậy, MAPE phù hợp với báo cáo kinh doanh vì giúp đánh giá sai số theo tỷ lệ, dễ hiểu hơn khi doanh thu các tháng có quy mô khác nhau.

Trong kết quả của dự án, Ridge có:

```text
MAPE = 14,72%
```

Điều này nghĩa là trung bình mô hình Ridge dự báo lệch khoảng 14,72% so với doanh thu thực tế trên tập test. Dự án chọn mô hình theo MAPE vì chỉ số này dễ diễn giải và phản ánh trực tiếp mức sai lệch tương đối của dự báo doanh thu.

Tuy nhiên, MAPE có một điểm cần lưu ý: nếu doanh thu thực tế của một tháng thấp, chỉ cần lệch một khoản tiền vừa phải thì tỷ lệ sai số cũng có thể tăng mạnh. Do đó, khi đọc MAPE cần xem thêm MAE để biết sai số tuyệt đối bằng tiền là bao nhiêu.

### 5.3. Công thức và ý nghĩa của R2

R2, hay hệ số xác định, đo mức độ mô hình giải thích được biến động của doanh thu. Công thức ý nghĩa:

```text
R2 = 1 - Sai số bình phương của mô hình / Sai số bình phương khi dự báo bằng trung bình thực tế
```

Có thể hiểu đơn giản như sau: nếu không dùng mô hình, ta có thể dự báo mọi tháng bằng doanh thu trung bình của tập test. Đây là một cách dự báo rất cơ bản. R2 so sánh mô hình hiện tại với cách dự báo trung bình đó.

Nếu mô hình dự báo tốt hơn nhiều so với việc chỉ lấy trung bình, phần sai số của mô hình sẽ nhỏ hơn nhiều, từ đó R2 tiến gần về 1. Nếu mô hình không tốt hơn trung bình, R2 gần 0. Nếu mô hình còn tệ hơn việc lấy trung bình, R2 có thể âm.

R2 có ý nghĩa “mô hình có bắt được biến động lên xuống của doanh thu hay không” vì nó dùng sai số bình phương để so sánh mức độ lệch của mô hình với mức biến động tự nhiên của dữ liệu quanh giá trị trung bình. Nếu tháng doanh thu cao thì mô hình cũng dự báo cao, tháng doanh thu thấp thì mô hình cũng dự báo thấp, sai số bình phương sẽ nhỏ và R2 sẽ cao.

Trong kết quả của dự án, Ridge có:

```text
R2 = 0,9153
```

Điều này có thể diễn giải là mô hình Ridge giải thích được khoảng 91,53% biến động doanh thu trên tập kiểm tra. Nói cách khác, mô hình không chỉ dự báo gần về mặt giá trị, mà còn nắm được khá tốt xu hướng tăng giảm giữa các tháng.

Tuy nhiên, vì tập test chỉ gồm 5 tháng nên R2 cần được xem như chỉ số tham khảo. Trong bài toán này, MAPE vẫn là tiêu chí chính để chọn mô hình, còn R2 hỗ trợ đánh giá khả năng mô hình bắt được biến động doanh thu.

### 5.4. Kết quả đánh giá các mô hình

Kết quả đánh giá trên tập test tháng 1 đến tháng 5 năm 2025 như sau:

| Mô hình | MAE | MAPE | R2 |
|---|---:|---:|---:|
| Ridge | 304.208.076 | 14,72% | 0,9153 |
| XGBoost | 621.451.391 | 20,53% | 0,7494 |
| Gradient Boosting | 708.484.077 | 25,73% | 0,6783 |
| Random Forest | 663.962.942 | 29,09% | 0,7487 |

Ridge có MAE thấp nhất, MAPE thấp nhất và R2 cao nhất trong các mô hình được thử nghiệm. Vì vậy, Ridge được chọn làm mô hình chính để dự báo doanh thu năm 2026.

Kết quả này cho thấy với dữ liệu doanh thu theo tháng và số lượng quan sát không lớn, mô hình tuyến tính có regularization như Ridge phù hợp hơn các mô hình cây phức tạp. Các mô hình như Random Forest, Gradient Boosting và XGBoost có khả năng học quan hệ phi tuyến, nhưng cần nhiều dữ liệu hơn để phát huy ổn định.

## 6. Kết luận

Toàn bộ các mô hình đều sử dụng cùng một bộ input gồm 15 biến được tạo từ dữ liệu bán hàng theo tháng. Sự khác nhau nằm ở cách từng mô hình học mối quan hệ giữa input và doanh thu. Ridge học quan hệ tuyến tính có kiểm soát overfit; Random Forest lấy trung bình nhiều cây quyết định; Gradient Boosting học tuần tự để sửa sai; XGBoost là phiên bản boosting nâng cao có thêm cơ chế tối ưu và kiểm soát độ phức tạp.

Kết quả thực nghiệm cho thấy Ridge Regression là mô hình phù hợp nhất trong dự án, với MAPE đạt 14,72% và R2 đạt 0,9153. Mô hình này được sử dụng để tạo dự báo doanh thu thuần tháng 1 đến tháng 5 năm 2026, phục vụ cho việc so sánh với doanh thu thực tế và đánh giá hiệu quả thay đổi hoạt động kinh doanh.
