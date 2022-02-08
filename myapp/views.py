from django.shortcuts import render,redirect
from .models import User,Contact,Product,Wishlist,Cart,Transaction
from django.conf import settings
from django.core.mail import send_mail
import random
from .paytm import generate_checksum, verify_checksum
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse


# Create your views here.

def validate_email(request):
    email = request.GET.get('email', None)
    data = {
        'is_taken': User.objects.filter(email__iexact=email).exists()
    }
    return JsonResponse(data)

def initiate_payment(request):
    user=User.objects.get(email=request.session['email'])
    try:
        amount = int(request.POST['amount'])
    except Exception as e:
    	print(e)
    	return render(request, 'checkout.html', context={'error': 'Wrong Accound Details or amount'})

    transaction = Transaction.objects.create(made_by=user,amount=amount)
    transaction.save()
    merchant_key = settings.PAYTM_SECRET_KEY

    params = (
        ('MID', settings.PAYTM_MERCHANT_ID),
        ('ORDER_ID', str(transaction.order_id)),
        ('CUST_ID', str('jigar93776@gmail.com')),
        ('TXN_AMOUNT', str(transaction.amount)),
        ('CHANNEL_ID', settings.PAYTM_CHANNEL_ID),
        ('WEBSITE', settings.PAYTM_WEBSITE),
        # ('EMAIL', request.user.email),
        # ('MOBILE_N0', '9911223388'),
        ('INDUSTRY_TYPE_ID', settings.PAYTM_INDUSTRY_TYPE_ID),
        ('CALLBACK_URL', 'http://localhost:8000/callback/'),
        # ('PAYMENT_MODE_ONLY', 'NO'),
    )

    paytm_params = dict(params)
    checksum = generate_checksum(paytm_params, merchant_key)

    transaction.checksum = checksum
    transaction.save()
    carts=Cart.objects.filter(user=user,status=False)
    for i in carts:
    	i.status=True
    	i.save()
    carts1=Cart.objects.filter(user=user,status=True)
    request.session['order_count']=len(carts1)
    paytm_params['CHECKSUMHASH'] = checksum
    print('SENT: ', checksum)
    return render(request, 'redirect.html', context=paytm_params)

@csrf_exempt
def callback(request):
    if request.method == 'POST':
        received_data = dict(request.POST)
        paytm_params = {}
        paytm_checksum = received_data['CHECKSUMHASH'][0]
        for key, value in received_data.items():
            if key == 'CHECKSUMHASH':
                paytm_checksum = value[0]
            else:
                paytm_params[key] = str(value[0])
        # Verify checksum
        is_valid_checksum = verify_checksum(paytm_params, settings.PAYTM_SECRET_KEY, str(paytm_checksum))
        if is_valid_checksum:
            received_data['message'] = "Checksum Matched"
        else:
            received_data['message'] = "Checksum Mismatched"
            return render(request, 'callback.html', context=received_data)
        return render(request, 'callback.html', context=received_data)


def index(request):
	try:
		user=User.objects.get(email=request.session['email'])
		products=Product.objects.all()
		wishlists=Wishlist.objects.filter(user=user)
		request.session['wishlist_count']=len(wishlists)
		carts=Cart.objects.filter(user=user,status=False)
		request.session['cart_count']=len(carts)
		net_price=0
		for i in carts:
			net_price=net_price+i.total_price
		total_item=len(carts)
		
		return render(request,'index.html',{'products':products,'carts':carts,'net_price':net_price,'total_item':total_item})
	except:
		return render(request,'index.html')

def seller_index(request):
	return render(request,'seller_index.html')

def signup(request):
	if request.method=="POST":
		try:
			User.objects.get(email=request.POST['email'])
			msg="Email Already Registered"
			return render(request,'signup.html',{'msg':msg})
		except:	
			if request.POST['password']==request.POST['cpassword']:
				User.objects.create(
						fname=request.POST['fname'],
						lname=request.POST['lname'],
						email=request.POST['email'],
						mobile=request.POST['mobile'],
						address=request.POST['address'],
						password=request.POST['password'],
						image=request.FILES['image'],
						usertype=request.POST['usertype']
					)
				msg="User Sign Up Successfull"
				return render(request,'login.html',{'msg':msg})
			else:
				msg="Password & Confirm Password Does Not Matched"
				return render(request,'signup.html',{'msg':msg})
	else:
		return render(request,'signup.html')

def contact(request):
	if request.method=="POST":
		Contact.objects.create(
				name=request.POST['name'],
				email=request.POST['email'],
				mobile=request.POST['mobile'],
				remarks=request.POST['remarks']
			)
		msg="Contact Saved Successfully"
		contacts=Contact.objects.all().order_by('-id')[:3]
		return render(request,'contact.html',{'msg':msg,'contacts':contacts})
	else:
		contacts=Contact.objects.all().order_by('-id')[:3]
		return render(request,'contact.html',{'contacts':contacts})

def login(request):
	if request.method=="POST":
		try:
			user=User.objects.get(
				email=request.POST['email'],
				password=request.POST['password']
			)
			if user.usertype=="user":
				request.session['email']=user.email
				request.session['fname']=user.fname
				request.session['image']=user.image.url
				products=Product.objects.all()
				wishlists=Wishlist.objects.filter(user=user)
				request.session['wishlist_count']=len(wishlists)
				carts=Cart.objects.filter(user=user,status=False)
				request.session['cart_count']=len(carts)
				carts1=Cart.objects.filter(user=user,status=True)
				request.session['order_count']=len(carts1)
				net_price=0
				for i in carts:
					net_price=net_price+i.total_price
				total_item=len(carts)
				return render(request,'index.html',{'products':products,'carts':carts,'net_price':net_price,'total_item':total_item})
			elif user.usertype=="seller":
				request.session['email']=user.email
				request.session['fname']=user.fname
				request.session['image']=user.image.url
				return render(request,'seller_index.html')
		except:
			msg="Email Or Password Is Incorrect"
			return render(request,'login.html',{'msg':msg})
	else:
		return render(request,'login.html')

def logout(request):
	try:
		del request.session['email']
		del request.session['fname']
		del request.session['image']
		del request.session['wishlist_count']
		del request.session['cart_count']
		return render(request,'login.html')
	except:
		return render(request,'login.html')

def change_password(request):
	if request.method=="POST":
		user=User.objects.get(email=request.session['email'])
		if user.password==request.POST['old_password']:
			if request.POST['new_password']==request.POST['cnew_password']:
				user.password=request.POST['new_password']
				user.save()
				return redirect('logout')
			else:
				msg="New Password & Confirm New Password Does Not Matched"
				return render(request,'change_password.html',{'msg':msg})
		else:
			msg="Old Password Is Incorrect"
			return render(request,'change_password.html',{'msg':msg})
	else:
		return render(request,'change_password.html')

def seller_change_password(request):
	if request.method=="POST":
		user=User.objects.get(email=request.session['email'])
		if user.password==request.POST['old_password']:
			if request.POST['new_password']==request.POST['cnew_password']:
				user.password=request.POST['new_password']
				user.save()
				return redirect('logout')
			else:
				msg="New Password & Confirm New Password Does Not Matched"
				return render(request,'seller_change_password.html',{'msg':msg})
		else:
			msg="Old Password Is Incorrect"
			return render(request,'seller_change_password.html',{'msg':msg})
	else:
		return render(request,'seller_change_password.html')

def forgot_password(request):
	if request.method=="POST":
		try:
			user=User.objects.get(email=request.POST['email'])
			otp=random.randint(1000,9999)
			subject = 'OTP For Forgot Password'
			message = 'Your OTP For Forgot Password Is '+str(otp)
			email_from = settings.EMAIL_HOST_USER
			recipient_list = [user.email, ]
			send_mail( subject, message, email_from, recipient_list )
			return render(request,'otp.html',{'email':user.email,'otp':otp})
		except:
			msg="Email Not Registered"
			return render(request,'forgot_password.html',{'msg':msg})
	else:
		return render(request,'forgot_password.html')

def verify_otp(request):
	email=request.POST['email']
	otp=request.POST['otp']
	uotp=request.POST['u_otp']

	if otp==uotp:
		return render(request,'new_password.html',{'email':email})
	else:
		msg="Invalid OTP"
		return render(request,'otp.html',{'email':email,'otp':otp,'msg':msg})

def new_password(request):
	email=request.POST['email']
	npassword=request.POST['new_password']
	cnpassword=request.POST['cnew_password']

	if npassword==cnpassword:
		user=User.objects.get(email=email)
		user.password=npassword
		user.save()
		return redirect('login')
	else:
		msg="New Password & Confirm New Password Does Not Matched"
		return render(request,'new_password.html',{'email':email,'msg':msg})

def seller_add_product(request):
	if request.method=="POST":
		user=User.objects.get(email=request.session['email'])	
		Product.objects.create(
				product_seller=user,
				product_category=request.POST['product_category'],
				product_company=request.POST['product_company'],
				product_model=request.POST['product_model'],
				product_desc=request.POST['product_desc'],
				product_price=request.POST['product_price'],
				product_image=request.FILES['product_image']
			)
		msg="Product Added Successfully"
		return render(request,'seller_add_product.html',{'msg':msg})
	else:
		return render(request,'seller_add_product.html')

def seller_view_product(request):
	seller=User.objects.get(email=request.session['email'])
	products=Product.objects.filter(product_seller=seller)
	return render(request,'seller_view_product.html',{'products':products})

def seller_edit_product(request,pk):
	product=Product.objects.get(pk=pk)
	if request.method=="POST":
		product.product_model=request.POST['product_model']
		product.product_desc=request.POST['product_desc']
		product.product_price=request.POST['product_price']
		try:
			product.product_image=request.FILES['product_image']
		except:
			pass
		product.save()
		msg="Product Updated Successfully"
		return render(request,'seller_edit_product.html',{'product':product,'msg':msg})
	else:
		return render(request,'seller_edit_product.html',{'product':product})

def seller_delete_product(request,pk):
	product=Product.objects.get(pk=pk)
	product.delete()
	return redirect('seller_view_product')

def product_filter(request,pc):
	products=Product()
	user=User.objects.get(email=request.session['email'])
	if pc=="All":
		products=Product.objects.all()
	else:
		products=Product.objects.filter(product_category=pc)
	carts=Cart.objects.filter(user=user,status=False)
	net_price=0
	for i in carts:
		net_price=net_price+i.total_price
	total_item=len(carts)
	return render(request,'index.html',{'products':products,'carts':carts,'net_price':net_price,'total_item':total_item})

def user_product_detail(request,pk):
	wishlist_flag=False
	cart_flag=False
	user=User.objects.get(email=request.session['email'])
	product=Product.objects.get(pk=pk)
	try:
		wishlist=Wishlist.objects.get(user=user,product=product)
		wishlist_flag=True
	except:
		pass
	try:
		cart=Cart.objects.get(user=user,product=product,status=False)
		cart_flag=True
	except:
		pass
	carts=Cart.objects.filter(user=user,status=False)
	net_price=0
	for i in carts:
		net_price=net_price+i.total_price
	total_item=len(carts)
	return render(request,'user_product_detail.html',{'product':product,'wishlist_flag':wishlist_flag,'cart_flag':cart_flag,'carts':carts,'net_price':net_price,'total_item':total_item})

def add_to_wishlist(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Wishlist.objects.create(
			user=user,
			product=product
		)
	net_price=0
	for i in carts:
		net_price=net_price+i.total_price
	total_item=len(carts)
	return redirect('wishlist')

def wishlist(request):
	user=User.objects.get(email=request.session['email'])
	wishlists=Wishlist.objects.filter(user=user)
	request.session['wishlist_count']=len(wishlists)
	carts=Cart.objects.filter(user=user,status=False)
	net_price=0
	for i in carts:
		net_price=net_price+i.total_price
	total_item=len(carts)
	return render(request,'wishlist.html',{'wishlists':wishlists,'carts':carts,'net_price':net_price,'total_item':total_item})

def remove_from_wishlist(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	wishlist=Wishlist.objects.get(user=user,product=product)
	wishlist.delete()

	return redirect('wishlist')

def cart(request):
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,status=False)
	request.session['cart_count']=len(carts)
	net_price=0
	for i in carts:
		net_price=net_price+i.total_price
	total_item=len(carts)
	return render(request,'cart.html',{'carts':carts,'net_price':net_price,'total_item':total_item})

def add_to_cart(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Cart.objects.create(
			user=user,
			product=product,
			product_price=product.product_price,
			total_price=product.product_price
		)
	return redirect('cart')

def remove_from_cart(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	cart=Cart.objects.get(user=user,product=product,status=False)
	cart.delete()
	return redirect('cart')

def checkout(request):
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,status=False)
	net_price=0
	for i in carts:
		net_price=net_price+i.total_price
	return render(request,'checkout.html',{'user':user,'carts':carts,'net_price':net_price})

def myorder(request):
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,status=True)
	return render(request,'myorder.html',{'carts':carts})