# AiR-Helix-View


### backend

pip install backend deps
```pip install flask flask-cors neo4j python-dotenv sentence-transformers pillow numpy```

to start backend:
cd to ```./backend```
run ```python app.py```


### frontend

npm install frontend deps:
```cd frontend```
```npm install```

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


---

for admin tasks, while backend running goto:
```http://127.0.0.1:5001/admin```
