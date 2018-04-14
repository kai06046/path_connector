# Path Connector

```
Usage: python main.py
```

## Meta Format


- self.results_dict
	- 存結果的 dict of dict, key 是蟲的 index, 包含的 keys 是被 detect 到的 frame, 中心和寬高
	- ```
	  {'1': {'path': [(100, 100), (105, 104)],
         'n_frame': [1, 10],
         'wh': [(50, 30), (55, 30)]},
         '2': {'path': [(300, 400), (301, 407)],
         'n_frame': [1, 2],
         'wh': [(50, 30), (55, 30)]}
	  }
	  ```

- self.tmp_results_dict
	- manual label model 時用來畫圖的暫時記憶
	- same format as self.results_dict

- self.dist_records
	- dict of dict of dict, 用來存判斷每個 bounding box 與上一 frame 每只埋葬蟲的距離
		- first key: nframe
		- second key: beetle index
		- third key: 'dist', 'center', 'below_tol', 'wh'
	- 假設第 1 frame 有兩隻蟲 ('1', '2')，3個 bounding box (你想的沒錯，這樣存很浪費...)
	``` 
	 {1 : {'1': {'dist': [0, 100, 200], 
	              'center': [(30, 40), (100, 100), (50, 80)], 
				  'below_tol': [True, False, False],
				  'wh': [(20, 30), (30, 20), (60，50)]},
		    '2': {'dist': [50, 0, 300], 
				  'center': [(30, 40), (100, 100), (50, 80)], 
				  'below_tol': [False, True, False],
				  'wh': [(20, 30), (30, 20), (60，50)]}
		   },
	   ...
	  }	  
  ```
	  
- self.hit_condi
	- 用來判斷的東西，list of tuple (蟲 index, 符合距離的 bounding box index)
	- ```
	  [('1', 0), ('2', 1), ('3', 0)] # '1' 蟲和第 0 個 bounding box 最近, '2' 蟲和第 1 個 bounding box 最近
	  ```

- self.stop_n_frame
	- 記錄出現問號 (邏輯判斷停下來) 的 frame
	- ```100```

- self.undone_pts, # 沒被分配的的框框

- self.current_pts
	- 當下問號框框的中心
	- ```(100, 50)```

- self.current_pts_n
	- 發生問號框框的 n frame
	- ```100 # 會和 self.stop_n_frame 一樣, 我有點忘了為何要另外加了```

- self.suggest_ind
	- 停下來後自動建議的選項
		- 'fp': false positive
		- 'new': 建議新蟲
		- stop frame 沒被分配到框框的蟲的 index ('1'/'2'/'3')
	- ``` 
	  [('new', {'assigned': ('2', 226.01991062736045),
   			  'not_assigned': ('4', 249.8259394058191)})]
	  ```

- self.object_name
	- dict of dict, key 是蟲的 index，包含的 keys 是 display name, ind 好像是 color index, on 是有沒有被 remove
	- ```
		{'1': {'display_name': 'A', 'ind': 0, 'on': True},
		 '2': {'display_name': '2', 'ind': 1, 'on': True},
		 '3': {'display_name': '3', 'ind': 2, 'on': True},
		 '4': {'display_name': '4', 'ind': 3, 'on': True}}
		```

