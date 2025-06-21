from fastapi import FastAPI, UploadFile, File

app = FastAPI()

@app.get("/")
def data():
    return {"filename":'data'}

@app.get("/about")
def about():
    return {'id':{'name':'Dixson','Age':10}}
@app.get("/about/unpublished")
def unpublished():
    return {'all unpublished data'}
@app.get('/about/{id}')
def new(id:int):
    return {id:about()}
@app.get("/about/{id}/comments")
def story():
    return 'data' 
