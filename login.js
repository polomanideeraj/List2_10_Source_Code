"use strict";

document.addEventListener("DOMContentLoaded",()=>{
    const $=id=>document.getElementById(id);
    const loginForm=$("loginForm");
    const registerForm=$("registerForm");
    const customerRole=$("customerRole");
    const employeeRole=$("employeeRole");
    const roleSelection=$("roleSelection");
    const customerName=$("customerName");
    const customerEmail=$("customerEmail");
    const employeeId=$("employeeId");
    const password=$("customerPassword");
    const passwordLabel=$("passwordLabel");
    const togglePassword=$("togglePassword");
    const loginButton=$("loginButton");
    const loginMessage=$("loginMessage");
    const registerMessage=$("registerMessage");
    const registerButton=$("registerButton");
    const registerPrompt=$("registerPrompt");

    let selectedRole="customer";

    function message(element,text,type="error"){
        element.textContent=text;
        element.className="message";
        if(type) element.classList.add(type);
    }

    function clearMessages(){
        message(loginMessage,"","");
        message(registerMessage,"","");
    }

    function selectRole(role){
        selectedRole=role;
        loginForm.hidden=false;
        registerForm.hidden=true;
        roleSelection.hidden=false;
        registerPrompt.hidden=role==="employee";

        customerRole.classList.toggle("active",role==="customer");
        employeeRole.classList.toggle("active",role==="employee");
        customerRole.setAttribute("aria-pressed",String(role==="customer"));
        employeeRole.setAttribute("aria-pressed",String(role==="employee"));

        $("customerNameGroup").hidden=role!=="customer";
        $("customerEmailGroup").hidden=role!=="customer";
        $("employeeIdGroup").hidden=role!=="employee";

        customerName.required=role==="customer";
        customerEmail.required=role==="customer";
        employeeId.required=role==="employee";
        password.required=true;

        customerName.value="";
        customerEmail.value="";
        employeeId.value="";
        password.value="";
        password.type="password";
        togglePassword.textContent="Show";

        passwordLabel.textContent=role==="customer"?"4-digit MPIN":"Password";
        password.name=role==="customer"?"mpin":"password";
        password.placeholder=role==="customer"?"Enter your 4-digit MPIN":"Enter your password";
        password.inputMode=role==="customer"?"numeric":"text";
        password.maxLength=role==="customer"?4:100;
        togglePassword.setAttribute("aria-label",role==="customer"?"Show MPIN":"Show password");

        $("formTitle").textContent=role==="customer"?"Welcome Back!":"Employee Login";
        $("formDescription").textContent=role==="customer"?"Sign in to access your FinAssist account.":"Sign in to access the employee portal.";
        $("formEyebrow").textContent=role==="customer"?"YOUR PERSONAL ASSISTANT":"EMPLOYEE PORTAL";
        $("welcomeIcon").textContent=role==="customer"?"👋":"💼";
        loginButton.innerHTML=role==="customer"?"Login <span>→</span>":"Employee Login <span>→</span>";

        clearMessages();
    }

    function showRegistration(){
        if(selectedRole!=="customer") return;
        loginForm.hidden=true;
        registerForm.hidden=false;
        roleSelection.hidden=true;
        registerPrompt.hidden=true;

        $("formTitle").textContent="Create Account";
        $("formDescription").textContent="Create your FinAssist customer account.";
        $("formEyebrow").textContent="JOIN FINASSIST";
        $("welcomeIcon").textContent="✦";
        clearMessages();
    }

    function returnToLogin(){
        selectRole("customer");
        $("formTitle").textContent="Welcome Back!";
    }

    customerRole.addEventListener("click",()=>selectRole("customer"));
    employeeRole.addEventListener("click",()=>selectRole("employee"));
    $("showRegister").addEventListener("click",showRegistration);
    $("showLogin").addEventListener("click",returnToLogin);

    togglePassword.addEventListener("click",()=>{
        const visible=password.type==="password";
        password.type=visible?"text":"password";
        togglePassword.textContent=visible?"Hide":"Show";
        togglePassword.setAttribute("aria-label",visible?"Hide password":"Show password");
    });

    document.querySelectorAll("[data-toggle]").forEach(button=>{
        button.addEventListener("click",()=>{
            const input=$(button.dataset.toggle);
            if(!input) return;
            const visible=input.type==="password";
            input.type=visible?"text":"password";
            button.textContent=visible?"Hide":"Show";
            button.setAttribute("aria-label",visible?"Hide MPIN":"Show MPIN");
        });
    });

    [password,$("registerMpin"),$("confirmMpin")].forEach(input=>{
        input.addEventListener("input",()=>{
            if(input.inputMode==="numeric"){
                input.value=input.value.replace(/\D/g,"").slice(0,4);
            }
        });
    });

    $("registerPhone").addEventListener("input",event=>{
        event.target.value=event.target.value.replace(/\D/g,"").slice(0,10);
    });

    loginForm.addEventListener("submit",async event=>{
        event.preventDefault();
        clearMessages();

        const enteredPassword=password.value;
        let payload;

        if(selectedRole==="customer"){
            const name=customerName.value.trim();
            const email=customerEmail.value.trim();

            if(!name||!email||!enteredPassword){
                message(loginMessage,"Please enter your name, email and MPIN.");
                return;
            }

            if(!/^\d{4}$/.test(enteredPassword)){
                message(loginMessage,"MPIN must contain exactly 4 digits.");
                return;
            }

            payload={role:"customer",name,email,mpin:enteredPassword};
        }else{
            const userId=employeeId.value.trim();

            if(!userId||!enteredPassword){
                message(loginMessage,"Please enter your employee ID and password.");
                return;
            }

            payload={role:"employee",user_id:userId,password:enteredPassword};
        }

        loginButton.disabled=true;
        message(loginMessage,"Signing in...","loading");

        try{
            const response=await fetch("/api/login",{
                method:"POST",
                credentials:"same-origin",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify(payload)
            });

            const result=await response.json();

            if(!response.ok||!result.success){
                throw new Error(result.message||"Login failed.");
            }

            if(!result.redirect){
                throw new Error("Login succeeded, but no destination page was provided.");
            }

            sessionStorage.clear();
            sessionStorage.setItem("userRole",result.role);

            if(result.role==="customer"){
                sessionStorage.setItem("customerId",result.customer.customer_id);
                sessionStorage.setItem("customerName",result.customer.name);
                sessionStorage.setItem("customerEmail",result.customer.email);
            }else{
                sessionStorage.setItem("employeeId",result.employee_id);
                sessionStorage.setItem("employeeName",result.employee_name||"Bank Employee");
            }

            window.location.replace(result.redirect);
        }catch(error){
            message(loginMessage,error.message||"Unable to connect to the server.");
        }finally{
            loginButton.disabled=false;
        }
    });

    registerForm.addEventListener("submit",async event=>{
        event.preventDefault();
        clearMessages();

        const name=$("registerName").value.trim();
        const email=$("registerEmail").value.trim();
        const phone=$("registerPhone").value.trim();
        const mpin=$("registerMpin").value;
        const confirmMpin=$("confirmMpin").value;
        const accountType=$("accountType").value;

        if(!name||!email||!phone||!mpin||!confirmMpin){
            message(registerMessage,"Please fill in all required fields.");
            return;
        }

        if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){
            message(registerMessage,"Please enter a valid email address.");
            return;
        }

        if(!/^\d{10}$/.test(phone)){
            message(registerMessage,"Enter a valid 10-digit mobile number.");
            return;
        }

        if(!/^\d{4}$/.test(mpin)){
            message(registerMessage,"MPIN must contain exactly 4 digits.");
            return;
        }

        if(mpin!==confirmMpin){
            message(registerMessage,"MPIN entries do not match.");
            return;
        }

        registerButton.disabled=true;
        message(registerMessage,"Creating your account...","loading");

        try{
            const response=await fetch("/api/register",{
                method:"POST",
                credentials:"same-origin",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({
                    name,email,phone,mpin,
                    confirm_mpin:confirmMpin,
                    account_type:accountType
                })
            });

            const result=await response.json();

            if(!response.ok||!result.success){
                throw new Error(result.message||"Registration failed.");
            }

            const customer=result.customer;
            const customerId=customer?.customer_id;

            registerForm.reset();
            selectRole("customer");
            customerName.value=name;
            customerEmail.value=email;

            $("formTitle").textContent="Account Created!";
            $("formDescription").textContent=customerId
                ?"Your customer ID is "+customerId+". Sign in using your name, email and MPIN."
                :"Your account was created. Please sign in.";
            $("formEyebrow").textContent="REGISTRATION SUCCESSFUL";
            $("welcomeIcon").textContent="✓";

            message(loginMessage,result.message||"Registration successful. Please log in.","success");
        }catch(error){
            message(registerMessage,error.message||"Unable to connect to the server.");
        }finally{
            registerButton.disabled=false;
        }
    });

    selectRole("customer");
});