# stock-utilities

stock_utilities ia a ```Python``` library for live and historical stock data support.


## Installation
Clone the repo using
```bash
git clone https://github.com/KMuchachi/stock-utilities.git
```
## Usage

#### Setup
* Activate a ```virtual environment``` or just use ```python3```

* install reqiurements
```bash
cd  stock-utilities
pip install -r stock_utils/requirements.txt
```
#### usage examples

##### Visualizing offline data
Run ```plot_existing_dataframe.py``` for this functionality.
You can alter the folowing for more customization
```python3
VALID_MOTION = 5
#an update function will only be called after scrolling through 5-1 min candles
UPDATE_SIZE = 100
#update the plot with 100 more candles if available
```

##### Visualizing online data
Run ```plot_live_data.py``` for this functionality.

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.


