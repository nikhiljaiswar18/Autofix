const express = require('express');
const mysql = require('mysql');
const app = express();

// Security: hardcoded database credentials
const db = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: 'admin123',
    database: 'users'
});

// Security: SQL injection
app.get('/user', (req, res) => {
    const id = req.query.id;
    db.query("SELECT * FROM users WHERE id = " + id, (err, result) => {
        res.json(result);
    });
});

// Security: XSS vulnerability
app.get('/greet', (req, res) => {
    const name = req.query.name;
    res.send(`<h1>Hello ${name}</h1>`);
});

// Bug: == instead of ===
function isAdmin(role) {
    if (role == 1) {
        return true;
    }
    return false;
}

// Bug: var instead of let (hoisting issue)
function processItems(items) {
    for (var i = 0; i < items.length; i++) {
        setTimeout(() => {
            console.log(items[i]); // Bug: always logs undefined
        }, 100);
    }
}

// Bug: missing await
async function fetchData(url) {
    const response = fetch(url);
    const data = response.json();  // Bug: response is a Promise
    return data;
}

// Security: eval on user input
app.post('/calc', (req, res) => {
    const result = eval(req.body.expression);
    res.json({ result });
});

// Bug: callback hell + no error handling
function saveUser(user, callback) {
    db.query("INSERT INTO users SET ?", user, (err, result) => {
        db.query("SELECT * FROM users WHERE id = " + result.insertId, (err, rows) => {
            db.query("INSERT INTO logs SET ?", { action: 'create', userId: rows[0].id }, (err) => {
                callback(rows[0]);
            });
        });
    });
}

// Security: no rate limiting, no input validation
app.listen(3000);
