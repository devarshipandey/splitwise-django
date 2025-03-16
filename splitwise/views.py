from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from splitwise import serializers, models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from rest_framework.request import Request
from rest_framework.settings import api_settings
from rest_framework.parsers import FormParser, MultiPartParser

def create_expense_common(data):
    """Shared expense creation logic for both API and frontend"""
    # Validate required fields
    required_fields = ['name', 'amount', 'paid_by', 'users']
    if any(field not in data for field in required_fields):
        raise ValueError("Missing required fields")

    # Convert data types
    data = data.copy()
    data['amount'] = float(data['amount'])
    
    # Get users
    paid_by_user = models.UserProfile.objects.get(email=data['paid_by'])
    participants = models.UserProfile.objects.filter(email__in=data['users'])
    
    # Validate expense name uniqueness
    if models.Expense.objects.filter(name=data['name']).exists():
        raise ValueError("Expense name must be unique")

    # Calculate shares
    num_participants = len(participants)
    if num_participants == 0:
        raise ValueError("At least one participant required")
    per_share = data['amount'] / num_participants

    # Handle group
    group = None
    if data.get('group_name'):
        group = models.Group.objects.get(group_name=data['group_name'])

    # Create expense records
    repayments = []
    expense_users = []
    
    for participant in participants:
        if participant != paid_by_user:
            # CORRECTED: Participant owes to payer
            debt = models.Debt.objects.create(
                from_user=participant,  # Debtor is the participant
                to_user=paid_by_user,  # Creditor is the payer
                amount=per_share
            )
            repayments.append(debt)

        expense_user = models.ExpenseUser.objects.create(
            user=participant,
            paid_share=per_share if participant == paid_by_user else 0,
            owed_share=per_share,
            net_balance=-per_share if participant != paid_by_user else (data['amount'] - per_share)
        )
        expense_users.append(expense_user)

    # Create main expense
    expense = models.Expense.objects.create(
        name=data['name'],
        description=data.get('description', ''),
        amount=data['amount'],
        expense_group=group
    )
    expense.repayments.set(repayments)
    expense.users.set(expense_users)
    
    return expense

class UserProfileApiView(APIView):
    """Test API View"""
    serializer_class = serializers.UserProfileSerializer

    def post(self, request) -> Response:
        """Create a hello message with our name"""
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            name = serializer.validated_data.get('name')
            return Response({'message': f'User {name} created successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateGroupApiView(APIView):
    """Group Creation View"""
    serializer_class = serializers.GroupSerializer

    def post(self, request) -> Response:
        """ Create a hello message with our name """

        all_users = []
        for user_email in request.data.get('members', []):
            all_users.append(models.UserProfile.objects.get(email=user_email).id)
        request.data['members'] = all_users
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': f'Group {serializer.data.get("group_name")} Created successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddUserToGroupApiView(APIView):
    """Add member to existing group Creation View"""

    def post(self, request) -> Response:
        """ Create a hello message with our name """
        group_name = request.data.get('group_name')
        user_email = request.data.get('user_email')
        user = models.UserProfile.objects.get(email=user_email)
        group = models.Group.objects.get(group_name=group_name)
        if user not in group.members.all():
            group.members.add(user.id)
            return Response({'message': f'User {user_email} successfully added to group {group.group_name}'})
        return Response({'message': 'User already exists in the group'}, status=status.HTTP_400_BAD_REQUEST)


class ShowGroupMembersApiView(APIView):
    """Show group members"""

    def get(self, request) -> Response:
        """ Create a hello message with our name """
        group_name = request.GET['name']
        try:
            group = models.Group.objects.get(group_name=group_name)
            # all_members = [x.name for x in group.members]
            all_members = [str(x) for x in group.members.all()]
            return Response({'message': f'{all_members}'})
        except models.Group.DoesNotExist:
            return Response(
                {'message': 'Group Does not exist !'
                 },
                status=status.HTTP_404_NOT_FOUND
            )


class ShowUserDetailsApiView(APIView):
    """Show user details"""
    def get(self, request) -> Response:
        try:
            user_email = request.GET['email']
            user = models.UserProfile.objects.get(email=user_email)
            
            # Get all debts where user is debtor or creditor
            debts_owed = models.Debt.objects.filter(from_user=user)
            debts_receivable = models.Debt.objects.filter(to_user=user)
            
            # Calculate totals
            total_owed = sum(debt.amount for debt in debts_owed)
            total_receivable = sum(debt.amount for debt in debts_receivable)
            
            # Build debt details
            debt_details = []
            for debt in debts_owed:
                debt_details.append(f"Owes ₹{debt.amount} to {debt.to_user.name}")
            for debt in debts_receivable:
                debt_details.append(f"Receiving ₹{debt.amount} from {debt.from_user.name}")
            
            return Response({
                'message': {
                    'user': str(user),
                    'total_owed': total_owed,
                    'total_receivable': total_receivable,
                    'debts': debt_details
                }
            })
        except models.UserProfile.DoesNotExist:
            return Response({'message': 'User not found'}, status=404)


# class CreateExpenseApiView(APIView):
#     """Group Creation View"""
#     serializer_class = serializers.ExpenseSerializer

#     def post(self, request) -> Response:
#         description = request.data.get('description')
#         all_users = request.data.get('users')
#         all_users = models.UserProfile.objects.filter(email__in=all_users)
#         paid_by = request.data.get('paid_by')
#         paid_by_user = models.UserProfile.objects.filter(email=paid_by).first()
#         amount = request.data.get('amount')
#         group_name = request.data.get('group_name', None)
#         expense_name = request.data.get('name')
#         if models.Expense.objects.filter(name=expense_name).count() > 0:
#             return Response({
#                 "message": "Expense name should be unique"
#             }, status=status.HTTP_400_BAD_REQUEST)
#         group = None
#         if group_name is not None:
#             group = models.Group.objects.get(group_name=group_name)
#         per_member_share = amount / len(all_users)
#         expense_users = []
#         repayments = []
#         for user in all_users:
#             if user != paid_by_user:
#                 debt = models.Debt.objects.create(**{"from_user": paid_by_user,
#                                                      "to_user": user,
#                                                      "amount": per_member_share})
#                 repayments.append(debt)
#             expense_user_dict = {"user": user,
#                                  "paid_share": 0 if user != paid_by_user else per_member_share,
#                                  "owed_share": per_member_share,
#                                  "net_balance": -per_member_share if user != paid_by_user else amount - per_member_share
#                                  }
#             expense_user = models.ExpenseUser.objects.create(**expense_user_dict)
#             expense_users.append(expense_user)
#         # now create expense
#         expense = {
#             'expense_group': group,
#             'description': description,
#             'amount': amount,
#             'name': expense_name
#         }
#         expense = models.Expense.objects.create(**expense)
#         expense.repayments.set(repayments)
#         expense.users.set(expense_users)
#         expense.save()
#         return Response({'message': 'Expense Created successfully'})

class CreateExpenseApiView(APIView):
    """API endpoint for expense creation"""
    serializer_class = serializers.ExpenseSerializer

    def post(self, request) -> Response:
        try:
            create_expense_common(request.data)
            return Response({'message': 'Expense Created successfully'})
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

class ShowGroupDetailsApiView(APIView):
    def get(self, request) -> Response:
        group_name = request.GET['name']
        try:
            group = models.Group.objects.get(group_name=group_name)
            expenses = models.Expense.objects.filter(expense_group=group, payment=False)
            data = list()
            for expense in expenses:
                exp = {
                    "name": expense.name,
                    "Description": expense.description,
                    "repayments": [str(x) for x in expense.repayments.all() if
                                   x.from_user != x.to_user and x.amount != 0]
                }
                data.append(exp)
            return Response(
                {'message': data
                 }
            )
        except models.Group.DoesNotExist:
            return Response(
                {'message': 'Group Does not exist !'
                 },
                status=status.HTTP_404_NOT_FOUND
            )


class DeleteUserApiView(APIView):
    def delete(self, request) -> Response:
        user_email = request.GET['email']
        try:
            user = models.UserProfile.objects.get(email=user_email)
            if user:
                user.delete()
                return Response(
                    {'message': 'User deleted'
                     }
                )
        except models.UserProfile.DoesNotExist:
            return Response({
                "message": "User does not exist"
            })


class DeleteGroupApiView(APIView):
    def delete(self, request) -> Response:
        group_name = request.GET['name']
        try:
            group = models.Group.objects.get(group_name=group_name)
            if group:
                group.delete()
                return Response(
                    {
                        'message': 'Group deleted'
                    }
                )
        except models.Group.DoesNotExist:
            return Response({
                "message": "Group does not exist"
            })

class RecordPaymentApiView(APIView):
    def post(self, request) -> Response:
        from_user_email = request.data.get('from_user')
        to_user_email = request.data.get('to_user')
        amount = request.data.get('amount')
        group_name = request.data.get('group_name')
        expense_name = request.data.get('expense_name')
        from_user = models.UserProfile.objects.get(email=from_user_email)
        to_user = models.UserProfile.objects.get(email=to_user_email)
        
        try:
            if group_name is None:
                # Create debt where payer is the receiver
                models.Debt.objects.create(
                    from_user=from_user,  # Debtor
                    to_user=to_user,      # Creditor
                    amount=amount
                )
                return Response({"message": "Payment recorded successfully"})
            
            else:
                # Group payment handling
                # ... existing code ...
                
                # Correct debt direction check
                existing_debt = None
                for debt in expense_name.repayments.all():
                    if debt.from_user == from_user and debt.to_user == to_user:
                        existing_debt = debt
                        break
                
                if existing_debt:
                    existing_debt.amount -= int(amount)
                    existing_debt.save()
                else:
                    new_debt = models.Debt.objects.create(
                        from_user=from_user,
                        to_user=to_user,
                        amount=-int(amount)
                    )
                    expense_name.repayments.add(new_debt)

                # Check if all debts are settled
                if all(debt.amount <= 0 for debt in expense_name.repayments.all()):
                    expense_name.payment = True
                    expense_name.save()

                return Response({"message": "Group payment recorded successfully"})
                
        except Exception as e:
            return Response({"message": str(e)}, status=400)
        
class UserDebtsApiView(APIView):
    """ Get current user's debts for the dropdown """
    def get(self, request):
        debts = models.Debt.objects.filter(
            from_user=request.user,
            amount__gt=0  # Only show unsettled debts
        ).select_related('to_user')
        
        debt_list = []
        for debt in debts:
            debt_list.append({
                'id': str(debt.id),
                'description': f"{debt.to_user.name} - ₹{debt.amount}",
                'to_user_email': debt.to_user.email,
                'amount': debt.amount
            })
        
        return Response(debt_list)

def settle_debt(request):
    if request.method == 'POST':
        try:
            debt = models.Debt.objects.get(
                id=request.POST.get('debt_id'),
                from_user=request.user,  # User is the debtor
                amount__gt=0
            )
            debt.delete()
            messages.success(request, f"Successfully settled debt to {debt.to_user.name}!")
        except models.Debt.DoesNotExist:
            messages.error(request, "Debt not found or already settled")
    return redirect('record-payment')


# ================== Frontend Views ==================

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    try:
        # Get user's groups and expenses
        user_groups = request.user.group_set.all()
        user_expenses = models.Expense.objects.filter(
            users__user=request.user
        ).select_related('expense_group')
        
        # Get debt summary using existing API logic
        mock_request = type('', (), {'GET': {'email': request.user.email}})()
        debt_response = ShowUserDetailsApiView().get(mock_request)
        debt_data = debt_response.data.get('message', {})
        
        return render(request, 'dashboard.html', {
            'groups': user_groups,
            'expenses': user_expenses,
            'debt_data': debt_data
        })
        
    except Exception as e:
        return render(request, 'error.html', {'error': str(e)})
        # Temporarily use login template for errors until we create error.html
        return render(request, 'login.html', {'error': f"Dashboard Error: {str(e)}"})

@login_required
def create_group(request):
    if request.method == 'POST':
        try:
            member_emails = request.POST.getlist('members', [])
            member_emails.append(request.user.email)  # Include current user
            
            # Convert emails to user IDs
            members = models.UserProfile.objects.filter(email__in=member_emails)
            member_ids = [member.id for member in members]

            data = {
                'group_name': request.POST.get('group_name'),
                'members': member_ids
            }

            serializer = serializers.GroupSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return redirect('group-detail', group_id=serializer.data['id'])
            
            return render(request, 'create_group.html', {
                'error': serializer.errors,
                'users': models.UserProfile.objects.exclude(id=request.user.id)
            })

        except Exception as e:
            return render(request, 'create_group.html', {'error': str(e)})
    
    return render(request, 'create_group.html', {
        'users': models.UserProfile.objects.exclude(id=request.user.id)
    })

@login_required
def group_detail(request, group_id):
    try:
        group = get_object_or_404(models.Group, id=group_id)
        expenses = models.Expense.objects.filter(expense_group=group)
        
        # Get members properly
        members = group.members.all()
        
        return render(request, 'group_detail.html', {
            'group': group,
            'expenses': expenses,
            'members': members  # Pass UserProfile objects directly
        })
        
    except Exception as e:
        return render(request, 'error.html', {
            'error': f"Error loading group: {str(e)}"
        })
        
    except Exception as e:
        return render(request, 'error.html', {'error': str(e)})

@login_required
@require_http_methods(["GET", "POST"])
def create_expense(request):
    if request.method == 'POST':
        try:
            # Convert participants to list
            participants = request.POST.getlist('participants', [])
            
            # Prepare form data
            form_data = {
                'name': request.POST.get('name'),
                'amount': request.POST.get('amount'),
                'description': request.POST.get('description', ''),
                'paid_by': request.POST.get('paid_by'),
                'users': [request.user.email] + participants,
                'group_name': request.POST.get('group_name') or None
            }

            # Validate and create expense
            create_expense_common(form_data)
            return redirect('dashboard')

        except Exception as e:
            # Preserve form input on error
            return render(request, 'create_expense.html', {
                'error': str(e),
                'groups': request.user.group_set.all(),
                'users': models.UserProfile.objects.exclude(id=request.user.id),
                'form_data': request.POST
            })
    
    # GET request - show empty form
    return render(request, 'create_expense.html', {
        'groups': request.user.group_set.all(),
        'users': models.UserProfile.objects.exclude(id=request.user.id)
    })

@login_required
def user_profile(request):
    """User profile view that reuses API logic"""
    try:
        # Create mock request for the API view
        mock_request = type('', (), {'GET': {'email': request.user.email}, 'method': 'GET'})()
        
        # Get API response
        api_response = ShowUserDetailsApiView().get(mock_request)
        
        # Extract data from API response
        response_data = api_response.data.get('message', {})
        
        # Format data for template
        formatted_data = {
            'user': request.user,
            'debit': abs(response_data.get('debit', 0)),
            'credit': response_data.get('credit', 0),
            'data': [
                entry.replace('User ', '').replace('user ', '')  # Clean up strings
                for entry in response_data.get('data', [])
            ]
        }
        
        return render(request, 'profile.html', formatted_data)
        
    except Exception as e:
        return render(request, 'error.html', {'error': f"Profile Error: {str(e)}"})
    
@login_required
def user_management(request):
    users = models.UserProfile.objects.exclude(id=request.user.id)
    return render(request, 'user_management.html', {'users': users})

@login_required
def delete_user(request, user_id):
    try:
        user = models.UserProfile.objects.get(id=user_id)
        user.delete()
        return redirect('user-management')
    except models.UserProfile.DoesNotExist:
        return render(request, 'error.html', {'error': 'User not found'})


@login_required
def delete_group(request, group_id):
    try:
        group = get_object_or_404(models.Group, id=group_id)
        
        # Optional: Add permission check
        if request.user not in group.members.all():
            return render(request, 'error.html', {'error': 'You are not authorized to delete this group'})
        
        group.delete()
        return redirect('dashboard')
        
    except Exception as e:
        return render(request, 'error.html', {'error': f"Error deleting group: {str(e)}"})
    
@login_required
def create_user(request):
    if request.method == 'POST':
        try:
            data = {
                'email': request.POST.get('email'),
                'name': request.POST.get('name'),
                'password': request.POST.get('password')
            }
            
            # Use your existing user creation logic
            user = models.UserProfile.objects.create_user(
                email=data['email'],
                name=data['name'],
                password=data['password']
            )
            return redirect('user-management')
            
        except Exception as e:
            return render(request, 'create_user.html', {'error': str(e)})
    
    return render(request, 'create_user.html')

# views.py
def static_test(request):
    return render(request, 'static_test.html')

@login_required
def record_payment(request):
    if request.method == 'POST':
        try:
            # Create DRF-compatible request
            drf_request = Request(
                request=request,
                parsers=[FormParser(), MultiPartParser()],
                authenticators=api_settings.DEFAULT_AUTHENTICATION_CLASSES
            )
            drf_request.user = request.user

            # Process payment
            api_view = RecordPaymentApiView()
            response = api_view.post(drf_request)

            if response.status_code == 200:
                messages.success(request, response.data.get('message'))
            else:
                messages.error(request, response.data.get('message', 'Payment failed'))
            
            return redirect('record-payment')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('record-payment')
    
    # GET request handling
    users = models.UserProfile.objects.exclude(email=request.user.email)
    groups = models.Group.objects.filter(members=request.user)
    
    # Get debts WHERE USER OWES MONEY TO OTHERS
    debts = models.Debt.objects.filter(
        from_user=request.user,
        amount__gt=0
    ).select_related('to_user')
    
    return render(request, 'record_payment.html', {
        'users': users,
        'groups': groups,
        'current_user': request.user,
        'debts': debts
    })