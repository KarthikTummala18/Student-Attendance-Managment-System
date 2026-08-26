const API_URL="https://student-attendance-managment-system.onrender.com";

const state={
  token:localStorage.getItem("edutrack_token"),
  user:null,
  page:"dashboard",
  cache:{},
  roleChoice:"student"
};

const $=s=>document.querySelector(s);

const api=async(path,opts={})=>{
  const headers={
    "Content-Type":"application/json",
    ...(opts.headers||{})
  };

  if(state.token){
    headers.Authorization=`Bearer ${state.token}`;
  }

  const res=await fetch(`${API_URL}${path}`,{
    ...opts,
    headers
  });

  if(!res.ok){
    let msg="Request failed";
    try{
      msg=(await res.json()).detail||msg
    }catch{}
    throw new Error(msg)
  }

  return res.json();
};

const initials=n=>
  (n||"U")
  .split(" ")
  .map(x=>x[0])
  .slice(0,2)
  .join("")
  .toUpperCase();

const toast=m=>{
  const x=document.createElement("div");
  x.className="toast";
  x.textContent=m;
  $("#toast-root").appendChild(x);
  setTimeout(()=>x.remove(),2600)
};

const fmt=d=>
  new Date(d).toLocaleDateString(undefined,{
    month:"short",
    day:"numeric",
    year:"numeric"
  });

const escapeHtml=s=>
  String(s??"").replace(
    /[&<>"']/g,
    c=>({
      "&":"&amp;",
      "<":"&lt;",
      ">":"&gt;",
      '"':"&quot;",
      "'":"&#39;"
    }[c])
  );

const pill=p=>
  p>=80
    ?`<span class="pill green">${p}%</span>`
    :p>=75
      ?`<span class="pill yellow">${p}%</span>`
      :`<span class="pill red">${p}%</span>`;

const modal=(title,body)=>{
  $("#modal-root").innerHTML=`
    <div class="modal-backdrop" id="modal">
      <div class="modal">
        <div class="modal-head">
          <h3>${title}</h3>
          <button class="close" onclick="closeModal()">×</button>
        </div>
        ${body}
      </div>
    </div>`;
};

const closeModal=()=>$("#modal-root").innerHTML="";
window.closeModal=closeModal;

const navConfig={
  student:[
    ["MAIN","dashboard","▦","Dashboard"],
    ["ACADEMICS","attendance","◉","Attendance"],
    ["","courses","▣","Courses"],
    ["","assignments","✓","Assignments"],
    ["","grades","◆","Grades"],
    ["","timetable","□","Timetable"],
    ["SERVICES","leave","↗","Leave Management"],
    ["","announcements","◌","Announcements"],
    ["","notifications","♢","Notifications"],
    ["","assistant","✦","AI Assistant"],
    ["ACCOUNT","profile","◎","Profile"]
  ],

  faculty:[
    ["MAIN","dashboard","▦","Dashboard"],
    ["TEACHING","students","♟","My Students"],
    ["","attendance","◉","Attendance"],
    ["","qr","▧","QR Attendance"],
    ["","analytics","◒","Analytics"],
    ["","leaves","↗","Leave Requests"],
    ["","assignments","✓","Assignments"],
    ["","grades","◆","Grades"],
    ["","timetable","□","Timetable"],
    ["COMMUNICATION","announcements","◌","Announcements"],
    ["","reports","▤","Reports"],
    ["","assistant","✦","AI Assistant"],
    ["ACCOUNT","profile","◎","Profile"]
  ],

  admin:[
    ["MAIN","dashboard","▦","Dashboard"],
    ["MANAGEMENT","students","♟","Students"],
    ["","faculty","♙","Faculty"],
    ["","departments","⌂","Departments"],
    ["","courses","▣","Courses"],
    ["","sections","▤","Sections"],
    ["","timetable","□","Timetable"],
    ["ANALYTICS","analytics","◒","Analytics"],
    ["","leaves","↗","Leave Management"],
    ["","announcements","◌","Announcements"],
    ["","reports","▤","Reports"],
    ["SECURITY","users","♚","Users & Roles"],
    ["","audit","◫","Audit Logs"],
    ["","settings","⚙","Settings"],
    ["","assistant","✦","AI Assistant"]
  ]
};

function setupNav(){
  const nav=$("#nav");
  nav.innerHTML="";

  (navConfig[state.user.role]||[]).forEach(
    ([section,id,icon,label])=>{
      if(section){
        nav.insertAdjacentHTML(
          "beforeend",
          `<div class="nav-section">${section}</div>`
        );
      }

      nav.insertAdjacentHTML(
        "beforeend",
        `<button class="nav-item ${state.page===id?"active":""}" data-page="${id}">
          <span>${icon}</span>${label}
        </button>`
      );
    }
  );

  nav.querySelectorAll(".nav-item").forEach(
    b=>b.onclick=()=>{
      state.page=b.dataset.page;
      setupNav();
      renderPage();
      $("#sidebar").classList.remove("open")
    }
  );
}

async function boot(){
  if(!state.token){
    return showLogin();
  }

  try{
    state.user=await api("/api/me");
    showApp();
    await renderPage()
  }catch{
    state.token=null;
    localStorage.removeItem("edutrack_token");
    showLogin()
  }
}

function showLogin(){
  document.body.classList.remove("in-app");
  $("#login-view").classList.remove("hidden");
  $("#app-view").classList.add("hidden")
}

function showApp(){
  $("#login-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");

  $("#sidebar-name").textContent=state.user.name;
  $("#sidebar-role").textContent=state.user.role;
  $("#sidebar-avatar").textContent=initials(state.user.name);
  $("#top-avatar").textContent=initials(state.user.name);

  setupNav();
  updateNotif();
}

$("#role-switch")?.addEventListener("click",()=>{});

document.querySelectorAll(".role-btn").forEach(
  b=>b.onclick=()=>{
    document
      .querySelectorAll(".role-btn")
      .forEach(x=>x.classList.remove("active"));

    b.classList.add("active");

    state.roleChoice=b.dataset.role;

    $("#email").value=
      state.roleChoice==="student"
        ?"student@edutrack.local"
        :state.roleChoice==="faculty"
          ?"faculty@edutrack.local"
          :"admin@edutrack.local";

    $("#password").value=
      state.roleChoice==="student"
        ?"student123"
        :state.roleChoice==="faculty"
          ?"faculty123"
          :"admin123";
  }
);

$("#show-password").onclick=()=>{
  $("#password").type=
    $("#password").type==="password"
      ?"text"
      :"password"
};

$("#login-form").onsubmit=async e=>{
  e.preventDefault();

  try{
    const r=await api("/api/login",{
      method:"POST",
      body:JSON.stringify({
        email:$("#email").value,
        password:$("#password").value
      })
    });

    state.token=r.token;

    localStorage.setItem(
      "edutrack_token",
      r.token
    );

    state.user=r.user;

    showApp();
    await renderPage()

  }catch(err){
    toast(err.message)
  }
};

$("#logout").onclick=async()=>{
  try{
    await api(
      "/api/logout",
      {method:"POST"}
    )
  }catch{}

  state.token=null;

  localStorage.removeItem(
    "edutrack_token"
  );

  showLogin()
};

$("#mobile-menu").onclick=()=>
  document
    .querySelector(".sidebar")
    .classList.toggle("open");

$("#notif-btn").onclick=()=>{
  state.page="notifications";
  setupNav();
  renderPage()
};

async function renderPage(){

  const title=
    state.page.replace(/-/g," ");

  $("#page-title").textContent=title;

  $("#breadcrumb").textContent=
    `${state.user.role} / ${title}`;

  const f={
    dashboard:pageDashboard,
    attendance:pageAttendance,
    courses:pageCourses,
    assignments:pageAssignments,
    grades:pageGrades,
    timetable:pageTimetable,
    leave:pageLeave,
    leaves:pageLeave,
    announcements:pageAnnouncements,
    notifications:pageNotifications,
    profile:pageProfile,
    assistant:pageAssistant,
    students:pageStudents,
    faculty:pageFaculty,
    departments:pageDepartments,
    sections:pageSections,
    analytics:pageAnalytics,
    qr:pageQR,
    reports:pageReports,
    users:pageUsers,
    audit:pageAudit,
    settings:pageSettings
  };

  try{
    await (f[state.page]||pageDashboard)()
  }catch(e){
    $("#page").innerHTML=`
      <div class="card">
        <b>Could not load this page.</b>
        <p class="muted">
          ${escapeHtml(e.message)}
        </p>
      </div>`
  }
}

async function get(k,url){
  return state.cache[k]||
    (state.cache[k]=await api(url))
}

function invalidate(...keys){
  keys.forEach(
    k=>delete state.cache[k]
  )
}