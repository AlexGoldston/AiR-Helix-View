# AiR-Helix-View

### backend
to start backend:
cd to ```./backend```
run ```python app.py```


### frontend
to start frontend:
in another terminal
cd to ```./frontend```
run ```npm start```

---

### current state

##### single node mode
![alt text](image-6.png)

##### extended graph mode - max neighbors
![alt text](image-5.png)

#### switch between Circular and Rectangular render mode for nodes
**circular mode** TODO:fix image distortion
![alt text](image-10.png)
**rectangular mode**
![alt text](image-11.png)

#### TAG filtering implemented
![alt text](image.png)

#### KEYWORD filetering implemented
![alt text](image-1.png)

##### INCREMENTAL DB UPDATES
![alt text](image-2.png)

basic run ```python database_update_incremental.py```
adv run ```python update_database_incremental.py --images-dir "/path/to/new/images" --threshold 0.4 --force-gpu --verbose```
use these flags:
```
--images-dir PATH     Directory containing images to add
--threshold FLOAT     Similarity threshold (default: 0.35)
--no-descriptions     Skip generating descriptions for images
--no-ml               Avoid using ML for descriptions (use basic descriptions only)
--force-gpu           Force GPU usage for descriptions when available
--verbose             Enable verbose output
```

---

# NOTE - admin curretly busted :: TODO: FIX HANG ON BACKEND ADMIN FEATURES...
for admin tasks, while backend running goto:
```http://127.0.0.1:5001/admin```
