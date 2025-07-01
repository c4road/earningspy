import pandas as pd

class LegacySaver:
    def save(   
        self, 
        pre_earning_data_path, 
        old_training_data_path, 
        new_training_data_path,
        overwrite=False
    ):
        """
        Save unprocesed pre earnings data without the items that were processed
        Merge old training data with new training data and store it
        """
        # Delete trained records from the calendar
        self.remaining_data = None

        if not overwrite and not new_training_data_path:
            raise Exception("store_path can't be empty if overwrite=False")

        data_saved = self.store_training_data(old_training_data_path, 
                                              new_training_data_path, 
                                              overwrite=overwrite)
        if self.remaining_data.empty:
            print('Unprocesed data is empty')
        else:
            try:
                print("Storing remaining data")
                self.remaining_data.to_csv(pre_earning_data_path)
            except: 
                print("Unable to store remaining data")

        return data_saved       

    def store_training_data(self, old_data_path, store_path, overwrite=True):

        if overwrite:
            store_path = old_data_path
        else:
            if not store_path:
                raise Exception("store_path can't be empty if overwrite=False")

        if self.new_training_data.empty:
            print("new data is empty nothing to concat")
            return
        old_data = pd.read_csv(old_data_path, index_col=0)
        old_data.index = pd.to_datetime(old_data.index)
        assert len(old_data.columns) == len(self.new_training_data.columns), \
            f"Different length of columns old={len(old_data.columns)} new={len(self.new_training_data.columns)}"

        self.merged_data = pd.concat([old_data, self.new_training_data], join='outer').drop_duplicates()
        try:
            self.merged_data.to_csv(store_path)
        except Exception as err:
            print(f"Unable to store data Error {str(err)}")
        else:
            print("Data stored successfully")
            return pd.read_csv(store_path, index_col=0, parse_dates=True)
