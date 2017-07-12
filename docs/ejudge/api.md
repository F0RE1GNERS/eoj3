# API

## 快速检索

+ `GET /reset` 配置页面（直接使用浏览器访问）
+ `POST /upload/case/:fid/:io` 上传测试用例，永久保存
+ `POST /upload/checker` 上传输出检查器，永久保存
+ `POST /upload/interactor` 上传交互程序，永久保存
+ `DELETE /delete/case/:fid` 删除指定的测试用例（不建议）
+ `DELETE /delete/checker/:fid` 删除指定的输出检查器（不建议）
+ `DELETE /delete/interactor/:fid` 删除指定的交互程序（不建议）
+ `POST /generate` 生成输入
+ `POST /validate` 验证输入
+ `POST /judge/result` 提交一组判题（往往用于测试）
+ `POST /judge/output` 根据输入和程序，生成输出
+ `POST /judge/sandbox` 返回程序运行的原始沙盒结果
+ `POST /judge/checker` 返回程序输出检查器的运行结果
+ `POST /judge/interactor` 返回交互程序的运行结果
+ `POST /judge` 提交判题

另有：socket.io `judge` 事件用于提交判题，格式与 `POST /judge` 相同。

注：不建议删除的原因是：容易造成业务逻辑混乱。

## RESTful API

### `POST /judge`


## Socket.io