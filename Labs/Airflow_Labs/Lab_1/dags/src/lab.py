import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans
from kneed import KneeLocator
import pickle
import os
import base64

def load_data():
    """
    Loads data from a CSV file, serializes it, and returns the serialized data.
    Returns:
        str: Base64-encoded serialized data (JSON-safe).
    """
    print("We are here")
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "../data/file.csv"))
    serialized_data = pickle.dumps(df)                    # bytes
    return base64.b64encode(serialized_data).decode("ascii")  # JSON-safe string

def data_preprocessing(data_b64: str):
    """
    Deserializes base64-encoded pickled data, performs preprocessing,
    and returns base64-encoded pickled clustered data.
    """
    # decode -> bytes -> DataFrame
    data_bytes = base64.b64decode(data_b64)
    df = pickle.loads(data_bytes)

    df = df.dropna()
    clustering_data = df[["BALANCE", "PURCHASES", "CREDIT_LIMIT"]]
    
    # CHANGE: handle outliers before scaling
    # clip each column to its 1st-99th percentile range
    lower = clustering_data.quantile(0.01)
    upper = clustering_data.quantile(0.99)
    n_clipped = int(((clustering_data < lower) | (clustering_data > upper)).sum().sum())
    print(f"Clipped {n_clipped} extreme values to the 1st-99th percentile range.")
    clustering_data = clustering_data.clip(lower=lower, upper=upper, axis=1)
 
    # log-transform to reduce the long right tail
    clustering_data = np.log1p(clustering_data)
 
    min_max_scaler = MinMaxScaler()
    clustering_data_minmax = min_max_scaler.fit_transform(clustering_data)
 
    # save the clipping bounds and scaler so the test data can be processed exactly the same way
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model")
    os.makedirs(model_dir, exist_ok=True)
    with open(os.path.join(model_dir, "preprocessor.pkl"), "wb") as f:
        pickle.dump({"lower": lower, "upper": upper,
                     "train_min": df[["BALANCE", "PURCHASES", "CREDIT_LIMIT"]].min(),
                     "train_max": df[["BALANCE", "PURCHASES", "CREDIT_LIMIT"]].max(),
                     "scaler": min_max_scaler}, f)

    # bytes -> base64 string for XCom
    clustering_serialized_data = pickle.dumps(clustering_data_minmax)
    return base64.b64encode(clustering_serialized_data).decode("ascii")


def build_save_model(data_b64: str, filename: str):
    """
    Builds a KMeans model on the preprocessed data and saves it.
    Returns the SSE list (JSON-serializable).
    """
    # decode -> bytes -> numpy array
    data_bytes = base64.b64decode(data_b64)
    df = pickle.loads(data_bytes)

    kmeans_kwargs = {"init": "random", "n_init": 10, "max_iter": 300, "random_state": 42}
    sse = []
    for k in range(1, 50):
        kmeans = KMeans(n_clusters=k, **kmeans_kwargs)
        kmeans.fit(df)
        sse.append(kmeans.inertia_)

    # NOTE: This saves the last-fitted model (k=49), matching your original intent.
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "wb") as f:
        pickle.dump(kmeans, f)

    return sse  # list is JSON-safe


def load_model_elbow(filename: str, sse: list):
    """
    Loads the saved model and uses the elbow method to report k.
    Returns the first prediction (as a plain int) for test.csv.
    """
    # load the saved (last-fitted) model
    output_path = os.path.join(os.path.dirname(__file__), "../model", filename)
    loaded_model = pickle.load(open(output_path, "rb"))

    # elbow for information/logging
    kl = KneeLocator(range(1, 50), sse, curve="convex", direction="decreasing")
    print(f"Optimal no. of clusters: {kl.elbow}")

    # CHANGE: process the test data the same way as the training data
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "../data/test.csv"))
    with open(os.path.join(os.path.dirname(__file__), "../model", "preprocessor.pkl"), "rb") as f:
        prep = pickle.load(f)
 
    # warn if a test value is outside the range the model was trained on
    for col in df.columns:
        value = df[col].iloc[0]
        if value < prep["train_min"][col] or value > prep["train_max"][col]:
            print(f"WARNING: {col} = {value:,.2f} is outside the training range "
                  f"({prep['train_min'][col]:,.2f} to {prep['train_max'][col]:,.2f}); "
                  f"it will be clipped and the prediction may be less reliable.")
 
    df = df.clip(lower=prep["lower"], upper=prep["upper"], axis=1)
    df = np.log1p(df)
    df = prep["scaler"].transform(df)
    print(f"Processed test data: {df.round(2).tolist()}")
 
    pred = loaded_model.predict(df)[0]


    # ensure JSON-safe return
    try:
        return int(pred)
    except Exception:
        # if not numeric, still return a JSON-friendly version
        return pred.item() if hasattr(pred, "item") else pred
