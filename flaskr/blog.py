from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, session,jsonify
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db
import sqlite3
from flask import session

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body, created, author_id, likes,username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    tags = db.execute('SELECT * FROM tags').fetchall()
    return render_template('blog/index.html', posts=posts,tags = tags)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        tags = request.form.getlist('tags')
        new_tag = request.form['new_tag'].strip()
        error = None

        if not title:
            error = 'Title is required.'
        elif not body:
            error = 'Body is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            try:
                cursor = db.cursor()

                # Insert into post table
                cursor.execute(
                    'INSERT INTO post (title, body, author_id) VALUES (?, ?, ?)',
                    (title, body, g.user['id'])
                )
                post_id = cursor.lastrowid  # 获取新插入的 post 记录的 id

                # Insert tags (existing and new)
                for tag_name in tags:
                    # Check if tag exists
                    tag = db.execute(
                        'SELECT id FROM tags WHERE name = ?',
                        (tag_name,)
                    ).fetchone()

                    if tag is None:
                        flash(f"Tag '{tag_name}' does not exist. Please choose from existing tags.")
                        return render_template('blog/create.html', tags=tags)

                    tag_id = tag['id']

                    # Insert into post_tags
                    cursor.execute(
                        'INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)',
                        (post_id, tag_id)
                    )

                # Insert new tag if provided
                if new_tag:
                    # Check if new_tag already exists
                    tag = db.execute(
                        'SELECT id FROM tags WHERE name = ?',
                        (new_tag,)
                    ).fetchone()

                    if tag is None:
                        # Insert new tag if it does not exist
                        cursor.execute(
                            'INSERT INTO tags (name) VALUES (?)',
                            (new_tag,)
                        )
                        tag_id = cursor.lastrowid
                    else:
                        tag_id = tag['id']

                    # Insert into post_tags
                    cursor.execute(
                        'INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)',
                        (post_id, tag_id)
                    )

                db.commit()
                return redirect(url_for('blog.index'))

            except db.IntegrityError as e:
                db.rollback()
                flash(f"Error occurred: {str(e)}")

            finally:
                cursor.close()

    db = get_db()
    tags = db.execute('SELECT * FROM tags').fetchall()
    return render_template('blog/create.html', tags=tags)

def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    # if check_author and post['author_id'] != g.user['id']:
    #     abort(403)

    return post

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))

@bp.route('/post/<int:id>', methods=('GET','POST'))
def details(id):
    post = get_post(id)
    db = get_db()
    if 'user_id' in session:
        user_id = session['user_id']
        user_like = db.execute(
            'SELECT id FROM likes WHERE user_id = ? AND post_id = ?',(user_id, id)
            ).fetchone()

    comments = db.execute(
        'SELECT c.id, c.body, c.created, u.username FROM comments c'
        ' JOIN user u ON c.user_id = u.id'
        ' WHERE c.post_id = ?'
        ' ORDER BY c.created ASC',
        (id,)
    ).fetchall()
    if request.method == 'POST':
        if 'user_id' in session:
            user_id = session['user_id']
            comment_body = request.form['body']
            db = get_db()
            db.execute(
                'INSERT INTO comments (post_id, user_id, body) VALUES (?, ?, ?)',
                (id, user_id, comment_body)
            )
            db.commit()
            return redirect(url_for('blog.details', id=id))
        else:
            return render_template('auth/login.html')

    return render_template('blog/details.html', post=post, comments=comments,id=id)


@bp.route('/post/<int:id>/like', methods=('POST','GET'))
@login_required
def like_post(id):
    db = get_db()
    if 'user_id' in session:
        user_id = session['user_id']
        # 这里可以继续处理点赞逻辑，使用 user_id 进行操作        
        try:
            user_like = db.execute(
            'SELECT id FROM likes WHERE user_id = ? AND post_id = ?',(user_id, id)
            ).fetchone()
            if user_like:
                # User has already liked this post, so we remove the like
                db.execute('DELETE FROM likes WHERE user_id = ? AND post_id = ?', (user_id, id))
                db.execute('UPDATE post SET likes = likes - 1 WHERE id = ?', (id,))
                db.commit()
            else:
                # User has not liked this post, so we add the like
                db.execute('INSERT INTO likes (user_id, post_id) VALUES (?, ?)', (user_id, id))
                db.execute('UPDATE post SET likes = likes + 1 WHERE id = ?', (id,))
                db.commit()
        except sqlite3.IntegrityError:
            # IntegrityError indicates duplicate like record
            pass
        finally:
            pass
        return redirect(url_for('blog.index', id=id))
    
    else:
        # 如果用户未登录，可以返回错误或跳转到登录页面
        return render_template('auth/login.html')

@bp.route('/posts_by_tag/<int:tag_id>', methods=['GET'])
def get_posts_by_tag(tag_id):
    conn = get_db()
    posts = conn.execute('''
        SELECT post.id, post.title, post.body, post.created, user.username
        FROM post
        JOIN post_tags ON post.id = post_tags.post_id
        JOIN tags ON post_tags.tag_id = tags.id
        JOIN user ON post.author_id = user.id
        WHERE tags.id = ?''', 
        (tag_id,)).fetchall()    
    posts_list = [dict(post) for post in posts]
    return jsonify(posts_list)