function showSubMenu(index){
    const mobileMenu02 = document.getElementById('mobileMenu' + index.toString());
        mobileMenu02.classList.remove('hide')
        mobileMenu02.classList.remove('transform-show');
}

function hideSubMenu(index){
    const mobileMenu02 = document.getElementById('mobileMenu' + index.toString());
    mobileMenu02.classList.add('transform-show');
    mobileMenu02.classList.add('hide')
}

function toggleX() {
    var hamburger = document.getElementById("hamburger");
    var cross = document.getElementById("cross");

    if (hamburger.classList.contains("hide")) {
        hamburger.classList.remove("hide");
        cross.classList.add("hide");
    } else {
        hamburger.classList.add("hide");
        cross.classList.remove("hide");

        const mobileMenu02 = document.getElementById('mobileMenu02');
        mobileMenu02.classList.remove('transform-show');

    }
}


