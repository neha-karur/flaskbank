from .. import all_module as am
from .utils import record_transaction

accounts_bp = am.Blueprint('accounts_bp', __name__)


@accounts_bp.route('/accounts/open', methods=['POST'])
@am.jwt_required
def open_account():
    data = am.request.get_json()
    if not data:
        return am.jsonify({'msg': 'Bad Request, no data received'}), 400

    try:
        alias = data['alias']
        acc_type = data['type']
        deposit = data['deposit']
    except KeyError:
        return am.jsonify({'msg': 'Bad Request, missing/misspelled key'}), 400

    current_user = am.get_jwt_identity()['username']
    account_num = am.get_account_num(acc_type)
    am.clients.update_one(
        {'username': current_user},
        {
            '$push':
            {
                'accounts': {
                    'account_number': account_num,
                    'alias': alias,
                    'balance': am.to_d128(deposit),
                    'type': acc_type,
                    'active': True,
                    'transactions': []
                }
            }
        }
    )

    if deposit:
        record_transaction(current_user, account_num, deposit, 'Initial '
                                                               'deposit')

    return am.jsonify({'msg': 'Account created',
                       'account_number': account_num,
                       'initial_deposit': deposit}), 201


@accounts_bp.route('/accounts/close/<string:account_num>', methods=['DELETE'])
@am.jwt_required
def close_account(account_num):

    if not am.verify(account_num):
        return am.jsonify({'msg': 'Invalid account number checksum'}), 422

    current_user = am.get_jwt_identity()['username']

    pre_update = am.clients.find_one_and_update(
        {'username': current_user},
        {
            '$pull': {
                'accounts': {'account_number': account_num}
            }
        }
    )
    exist = next((index for (index, d) in enumerate(pre_update['accounts'])
                  if d['account_number'] == account_num), None)

    if not exist:
        return am.jsonify({'msg': f'User {current_user} does not own '
                          f'account: {account_num}'}), 409

    return am.jsonify({'msg': f'Account {account_num} closed'}), 200


@accounts_bp.route('/accounts/delete', methods=['DELETE'])
def delete_one_client():
    data = am.request.get_json()
    if not data:
        return am.jsonify({'msg': 'Bad Request, no data received'}), 400
    try:
        username = data['username']
        password = data['password']
        email = data['email']
    except KeyError:
        return am.jsonify({'msg': 'Bad Request, missing/misspelled key'}), 400

    client = am.clients.find_one({'username': username})
    if not client:
        return am.jsonify({'msg': 'Invalid username/password'}), 409

    valid = am.bcrypt.check_password_hash(client['password'].decode('UTF-8'),
                                          password)
    
    if not valid or email != client['email']:
        return am.jsonify({'msg': 'Invalid username/email/password'}), 409

    result = am.clients.delete_one({'username': username})
    if result.deleted_count:
        return am.jsonify({'msg': f'user <{username}> deleted'}), 200
    return am.jsonify({'msg': f'user <{username}> does not exist'}), 409
