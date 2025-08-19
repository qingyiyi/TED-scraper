# TED爬虫程序

文件说明

```
——config.py
--requirements.txt
--run.py
--setup_edge_driver.py
--ted_scraper_edge.py
--ted_videos_edge_result.xlsx
--test_ted_access.py
```



**说明：**

本程序基于windows操作系统，使用edge浏览器抓取TED网站视频相关信息，并进行筛选，最终获取排名	视频标题	演讲者	视频链接	演讲时长	播放量	发布时间	transcript	URL	信息

> 注意运行程序时，关闭梯子


# 配置环境

* 下载edge driver放置于```D:/Drivers/```目录下并在该目录下解压，没有可以手动创建该目录，大小写一致

> [Microsoft Edge WebDriver | Microsoft Edge Developer](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver?form=MA13LH)



* 安装相关依赖，在terminal中项目目录下输入以下命令，要求python版本≥3.8

```
pip install -r requirements.txt
```



# 运行

* config中配置相关搜索参数

> 在文件中都有较为详细的参数说明，直接修改对应参数即可
>
> 确保只修改config.py等号后，或[]中的参数，不要随意修改其余部分代码

* 在终端运行下面命令开始获取相关信息

```bash
python ted_scraper_edge.py
```

等待程序运行，可以关注INFO信息，会提示进度，仅当出现中文报错失败才是程序执行失败，英文的error为网络原因，可以忽略



# 结果

将爬虫结果保存为txt文件，放置于transcripts目录下，若最终筛选后视频数少于100，则不会保存low view的transcript，所有transcript均直接抓取自ted网站，没有任何转录或修改，因此若有拼写错误等，均为ted原网站语音识别错误。

最后总览结果位于xslx文件下

