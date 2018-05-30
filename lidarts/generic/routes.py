from flask import render_template, redirect, url_for, request, jsonify
from flask_login import current_user, login_required
from lidarts import db
from lidarts.generic import bp
from lidarts.models import Game, User, Chatmessage, Friendship, FriendshipRequest
from lidarts.generic.forms import ChatmessageForm
from sqlalchemy import desc
from datetime import datetime, timedelta


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now()
        db.session.commit()


@bp.route('/')
def index():
    # logged in users do not need the index page
    if current_user.is_authenticated:
        return redirect(url_for('generic.lobby'))
    return render_template('generic/index.html')


@bp.route('/about')
def about():
    return render_template('generic/index.html')


@bp.route('/lobby')
@login_required
def lobby():
    player_names = {}
    games_in_progress = Game.query.filter(((Game.player1 == current_user.id) | (Game.player2 == current_user.id)) & \
                                          (Game.status == 'started')).order_by(desc(Game.id)).all()
    for game in games_in_progress:
        if game.player1 and game.player1 not in player_names:
            player_names[game.player1] = User.query.with_entities(User.username) \
                .filter_by(id=game.player1).first_or_404()[0]
        if game.player2 and game.player2 not in player_names:
            player_names[game.player2] = User.query.with_entities(User.username) \
                .filter_by(id=game.player2).first_or_404()[0]

    friend_requests = FriendshipRequest.query.filter_by(receiving_user_id=current_user.id).all()
    for friend_request in friend_requests:
        if friend_request.requesting_user_id not in player_names:
            player_names[friend_request.requesting_user_id] = User.query.with_entities(User.username) \
                .filter_by(id=friend_request.requesting_user_id).first_or_404()[0]

    return render_template('generic/lobby.html', games_in_progress=games_in_progress, player_names=player_names,
                           friend_requests=friend_requests)


@bp.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    form = ChatmessageForm()
    messages = Chatmessage.query.filter(Chatmessage.timestamp > (datetime.now() - timedelta(days=1))).all()
    user_names = {}
    timestamps = {}

    for message in messages:
        user_names[message.author] = User.query.with_entities(User.username) \
            .filter_by(id=message.author).first_or_404()[0]

    return render_template('generic/chat.html', form=form, messages=messages,
                           user_names=user_names)


@bp.route('/validate_chat_message', methods=['POST'])
@login_required
def validate_chat_message():
    # validating the score input from users
    form = ChatmessageForm(request.form)
    result = form.validate()
    print(form.errors)
    return jsonify(form.errors)


@bp.route('/send_friend_request/<id>', methods=['POST'])
@login_required
def send_friend_request(id):
    id = int(id)
    friendship = Friendship.query \
        .filter(((Friendship.user1_id == id) & (Friendship.user2_id == current_user.id))
                | ((Friendship.user2_id == id) & (Friendship.user1_id == current_user.id))).first()

    if not friendship:
        friendship_request = FriendshipRequest.query \
            .filter(((FriendshipRequest.requesting_user_id == id) & (FriendshipRequest.receiving_user_id == current_user.id))
                    | ((FriendshipRequest.receiving_user_id == id) & (FriendshipRequest.requesting_user_id == current_user.id))).first()

        if not friendship_request:
            friendship_request = FriendshipRequest(requesting_user_id=current_user.id, receiving_user_id=id)
            db.session.add(friendship_request)
            db.session.commit()
    return jsonify('success')


@bp.route('/accept_friend_request/')
@bp.route('/accept_friend_request/<id>', methods=['POST'])
@login_required
def accept_friend_request(id):
    id = int(id)
    friendship_request = FriendshipRequest.query \
        .filter(((FriendshipRequest.requesting_user_id == id) &
                 (FriendshipRequest.receiving_user_id == current_user.id))
                | ((FriendshipRequest.receiving_user_id == id) &
                   (FriendshipRequest.requesting_user_id == current_user.id))).all()

    if friendship_request:
        friendship = Friendship(user1_id=friendship_request[0].requesting_user_id,
                                user2_id=friendship_request[0].receiving_user_id)
        db.session.add(friendship)

        for request in friendship_request:
            db.session.delete(request)

        db.session.commit()
        return jsonify('success')

    return jsonify('failure')


@bp.route('/decline_friend_request/')
@bp.route('/decline_friend_request/<id>', methods=['POST'])
@login_required
def decline_friend_request(id):
    id = int(id)
    friendship_request = FriendshipRequest.query \
        .filter(((FriendshipRequest.requesting_user_id == id) &
                 (FriendshipRequest.receiving_user_id == current_user.id))
                | ((FriendshipRequest.receiving_user_id == id) &
                   (FriendshipRequest.requesting_user_id == current_user.id))).all()

    if friendship_request:
        for request in friendship_request:
            db.session.delete(request)

        db.session.commit()
        return jsonify('success')

    return jsonify('failure')


@bp.route('/remove_friend/')
@bp.route('/remove_friend/<id>', methods=['POST'])
@login_required
def remove_friend(id):
    id = int(id)
    friendship = Friendship.query \
        .filter(((Friendship.user1_id == id) &
                 (Friendship.user2_id == current_user.id))
                | ((Friendship.user2_id == id) &
                   (Friendship.user1_id == current_user.id))).first()

    if friendship:
        db.session.delete(friendship)

        db.session.commit()
        return jsonify('success')

    return jsonify('failure')


@bp.route('/remove_friend_request/')
@bp.route('/remove_friend_request/<id>', methods=['POST'])
@login_required
def remove_friend_request(id):
    id = int(id)
    friendship_request = FriendshipRequest.query \
        .filter(((FriendshipRequest.requesting_user_id == current_user.id) &
                 (FriendshipRequest.receiving_user_id == id))).first()

    if friendship_request:
        db.session.delete(friendship_request)

        db.session.commit()
        return jsonify('success')

    return jsonify('failure')
