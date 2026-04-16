import java.sql.*;
import java.io.*;
import java.util.*;

public class UserService {
    // Security: hardcoded credentials
    private static final String DB_URL = "jdbc:mysql://localhost/users";
    private static final String DB_USER = "root";
    private static final String DB_PASS = "password123";

    // Security: SQL injection
    public User getUser(String userId) throws SQLException {
        Connection conn = DriverManager.getConnection(DB_URL, DB_USER, DB_PASS);
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE id = '" + userId + "'");
        // Bug: connection never closed (resource leak)
        if (rs.next()) {
            return new User(rs.getString("name"), rs.getString("email"));
        }
        return null; // Bug: caller doesn't check for null
    }

    // Bug: equals without hashCode
    public class User {
        String name;
        String email;

        User(String name, String email) {
            this.name = name;
            this.email = email;
        }

        @Override
        public boolean equals(Object obj) {
            if (obj instanceof User) {
                User other = (User) obj;
                return this.name.equals(other.name); // Bug: NPE if name is null
            }
            return false;
        }
        // Missing hashCode override!
    }

    // Security: path traversal
    public String readFile(String filename) throws IOException {
        BufferedReader reader = new BufferedReader(new FileReader("/data/" + filename));
        StringBuilder content = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            content.append(line);
        }
        // Bug: reader never closed
        return content.toString();
    }

    // Bug: ConcurrentModificationException
    public void removeInactive(List<User> users) {
        for (User user : users) {
            if (user.email == null) {
                users.remove(user); // Bug: modifying list during iteration
            }
        }
    }

    // Security: insecure deserialization
    public Object loadObject(String path) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream(path));
        return ois.readObject();
    }
}
