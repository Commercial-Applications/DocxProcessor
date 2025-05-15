
## Requires
* python-dox

## Description
Will modify Embedded URL's that match HTTPS? pattern and replace with [regex]
urls that do not match pattern are not changed.

Works with the document xml so does not require word to be opened for each file.

## Functional within:
* Body text
* Multiple sections of Header and Footer
* Is Case insensitive
* Both http and https are captured

## Pending:
* Tables (This is possible)

## Note:
There are some edge cases that may cause issues.
Works only on current word .docx (xml) not .doc

## License
Copyright (c) 2024 Sean Smith
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Installation
pip install git+[https://github.com/YOUR-USERNAME/docx-processor.git](https://github.com/Commercial-Applications/docx-processor.git)
