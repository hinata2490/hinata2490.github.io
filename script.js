const yearElement = document.getElementById("year");

if (yearElement) {
  yearElement.textContent = String(new Date().getFullYear());
}

const contactForm = document.querySelector(".contact-form");

if (contactForm) {
  contactForm.addEventListener("submit", (event) => {
    event.preventDefault();
  });
}

const workLinks = document.querySelectorAll(".card-link");

workLinks.forEach((link) => {
  // href="#" はダミーリンク。実URLに差し替えると通常リンクとして動きます。
  if (link.getAttribute("href") === "#") {
    link.addEventListener("click", (event) => {
      event.preventDefault();
    });
  }
});
