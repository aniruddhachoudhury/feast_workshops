import feast
from joblib import dump
import pandas as pd
from sklearn.linear_model import LinearRegression
import mlflow


class DriverRankingTrainModel:
    def __init__(self, repo_path: str) -> None:
        self._repo_path = repo_path

    def get_training_data(self) -> pd.DataFrame:

        # Load driver order data
        orders = pd.read_csv("./data/driver_orders.csv", sep="\t")
        orders["event_timestamp"] = pd.to_datetime(orders["event_timestamp"])

        # Connect to your local feature store
        # change this to your location
        fs = feast.FeatureStore(repo_path=self._repo_path)

        # Retrieve training data from BigQuery
        training_df = fs.get_historical_features(
            entity_df=orders,
            feature_refs=[
                "driver_hourly_stats:conv_rate",
                "driver_hourly_stats:acc_rate",
                "driver_hourly_stats:avg_daily_trips",
            ],
        ).to_df()
        return training_df

    def train_model(self) -> str:
        # Enable autologging for mlflow and set the tracking uri with the local model registry
        # SQLite db
        mlflow.set_tracking_uri("sqlite:///mlruns.db")
        mlflow.sklearn.autolog()

        # create model
        model = LinearRegression()
        target = "trip_completed"
        training_df = self.get_training_data()
        train_X = training_df[training_df.columns.drop(target).drop("event_timestamp")]
        train_y = training_df.loc[:, target]

        # log some parameters and Feast feature names
        with mlflow.start_run() as run:
            model.fit(train_X[sorted(train_X)], train_y)
            mlflow.log_param("feast_data", "driver_hourly_stats")
            mlflow.log_dict({"features": ["driver_hourly_stats:conv_rate", "driver_hourly_stats:acc_rate",
                                          "driver_hourly_stats:avg_daily_trips"]}, "feast_data.json")
        return {run.info.run_id}


if __name__ == '__main__':
    REPO_PATH = "/Users/jules/git-repos/feast_workshops/module_1/feature_repo"
    model_cls = DriverRankingTrainModel(REPO_PATH)
    run_id = model_cls.train_model()
    print (f"Model run id: {run_id}")

