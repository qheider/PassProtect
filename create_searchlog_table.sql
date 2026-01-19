-- Create searchlog table for tracking password search activity
-- This table is used by the searchTrackAgent to log user searches

CREATE TABLE IF NOT EXISTS searchlog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    search_date DATETIME NOT NULL,
    companyName VARCHAR(45) NOT NULL,
    search_by_user VARCHAR(45) NOT NULL,
    INDEX idx_user_date (search_by_user, search_date DESC),
    INDEX idx_company (companyName)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Optional: Add description comment
ALTER TABLE searchlog COMMENT = 'Logs password search activity for analytics and recent search tracking';
