自定义存储库

请求任务时，在请求头中添加oss参数即可

存储库id (必填)

oss-id

存储库路径 (选填, 当为空时则默认存储库根目录)

oss-path

请求头 Headers（示例）

{

&#x20; "Content-Type": "application/json",

&#x20; "Authorization": "Bearer apikey",

&#x20; "oss-id": "id",

&#x20; "oss-path": "file/images"

}



