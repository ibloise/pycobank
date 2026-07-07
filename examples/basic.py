from pycobank import PycoBank


db = PycoBank("../data/mycobank.sqlite3")

for record in db.nearest_names("Amanita muscarria", limit=5):
    print(record.summary())
