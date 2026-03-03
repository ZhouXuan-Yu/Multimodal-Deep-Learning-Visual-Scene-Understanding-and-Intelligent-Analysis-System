#数据库连接配置
import pymysql

conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='123456',  # 请修改为您本地MySQL的密码
        database='exam'
    )
'''
# 测试使用；连接数据库
import pymysql

def test_database_connection():
    try:
        # 连接到数据库
        connection = pymysql.connect(
            host="localhost",
            port=3306,
            user="root",
            password="123",
            database="exam",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )

        # 创建一个游标对象
        cursor = connection.cursor()

        # 执行一个简单的查询
        cursor.execute("SELECT VERSION()")
        db_version = cursor.fetchone()

        # 打印数据库版本信息
        print("Connected to the database successfully.")
        print("Database version:", db_version['VERSION()'])

        # 关闭游标和连接
        cursor.close()
        connection.close()

    except pymysql.Error as error:
        print("Error while connecting to MySQL:", error)

# 调用测试函数
test_database_connection()


'''
