# TheBestBookOn.com

![The Best Book On logo](https://thebestbookon.com/static/imgs/best-book-on.png)

## Philosophy

Book preference is a matter of taste, however, many people have similar tastes. One book may be perceived as better than another book in several ways, and in a combinations of these 10 ways (shown below). While we may be able to say one book is better than other if it is outperformed unanimously in every category, it likely makes more sense to compare books under the context of a specific criteria, for instance, its reading level or accuracy. Learn more about this direction at [Open Book Genome Project](https://bookgenomeproject.org).

## Installation

```bash
virtualenv venv
source venv/bin/activate
git clone https://github.com/Open-Book-Genome-Project/TheBestBookOn.com.git
cd thebestbookon.com
pip install -e .
cd /bestbook
python app.py

```

### Setting up the DB

First, create a user and a database for the project to use:

    $ sudo -u postgres psql
    postgres=# create user rex with password 'yourPasswordHere' login createdb;
    postgres=# create database bestbooks owner rex;
    
Next, create a file called `settings.cfg` with the following contents within `bestbook/configs/`. Replace `yourPasswordHere` with the value you choose when creating your pql database. Under the `[security]` section, fill in a value for `secret = ` by generating os.urandom(24) -- see: http://flask.pocoo.org/docs/0.10/quickstart/#sessions "How to generate good secret keys":

    [server]
    host = 0.0.0.0
    port = 8080
    debug = 1
    cors = 1
    
    [security]
    secret = 
    
    [db]
    user = rex
    pw = yourPasswordHere

#### Creating an Tables

Once your database and user have been created, and the user has the correct permissions, run the following:

    $ cd bestbook
    $ ls  # confirm you're in the package root
    api/ app.py configs/ ...
    $ python
    >>> import api
    >>> api.core.Base.metadata.create_all(api.engine)  # creates tables from sqlalchemy models inherited from api root

## Run server

    $ python app.py
    * Running on http://0.0.0.0:8080/ (Press CTRL+C to quit)

## Resources

- https://www.lesswrong.com/posts/xg3hXCYQPJkwHyik2/the-best-textbooks-on-every-subject
- http://www.tarleton.edu/departments/library/library_module/unit8/8books_lm.htm
- http://lib.colostate.edu/howto/evalbk.html
- http://www2.lib.unc.edu/instruct/evaluate/?section=books


## Similar

- https://fivebooks.com
